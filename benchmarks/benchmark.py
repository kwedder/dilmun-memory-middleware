"""
Dilmun vs. vector memory — reproducible micro-benchmark.

Run:  python benchmarks/benchmark.py

Measures the axes where a deterministic memory algebra should differ from
similarity-only retrieval:

  1. Current-value recall under updates  (does the store return the LATEST
     value after a fact is revised many times?)
  2. Determinism under insertion-order shuffles
  3. Duplicate suppression under predicate paraphrase (normalization)
  4. Write / query latency

The vector baseline is a TF-IDF cosine store (benchmarks/vector_baseline.py).
Everything is seeded; numbers are reproducible. This is a focused micro-
benchmark, NOT a standardized suite like LoCoMo/LongMemEval — see the README
Limitations section.
"""

from __future__ import annotations

import json
import random
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dilmun import DilmunMemory, PredicateRegistry
from benchmarks.vector_baseline import VectorMemory

SEED = 20260704
CITIES = ["Miami", "Orlando", "Tampa", "Naples", "Sarasota", "Ocala",
          "Jacksonville", "Gainesville", "Pensacola", "Tallahassee"]


def fresh_dilmun(predicates=None):
    tmp = tempfile.mkdtemp(prefix="dilmun_bench_")
    return DilmunMemory(tmp, predicates=predicates)


# ---------------------------------------------------------------------------
# 1. current-value recall under updates
# ---------------------------------------------------------------------------

def bench_current_value(n_entities=200, updates=5):
    """Each entity's 'city' is revised `updates` times with rising timestamps.
    Correct answer = the final (latest) value. Measures recall accuracy."""
    rng = random.Random(SEED)
    history = []  # (entity, [values in temporal order])
    for e in range(n_entities):
        vals = [rng.choice(CITIES) for _ in range(updates)]
        # ensure the last value differs from the first so "latest" is meaningful
        while vals[-1] == vals[0]:
            vals[-1] = rng.choice(CITIES)
        history.append((f"user{e}", vals))

    dil = fresh_dilmun()
    vec = VectorMemory()
    t = 0
    writes = []
    for entity, vals in history:
        for v in vals:
            t += 1
            writes.append((entity, "city", v, t))
    # write in temporal order for both stores
    for entity, pred, v, ts in writes:
        dil.write_fact(entity, pred, v, timestamp=float(ts))
        vec.write_fact(entity, pred, v)

    dil_correct = vec_correct = 0
    for entity, vals in history:
        latest = vals[-1]
        if dil.query(entity=entity, predicate="city") and \
                dil.query(entity=entity, predicate="city")[0].value == latest:
            dil_correct += 1
        if vec.recall_value(entity, "city") == latest:
            vec_correct += 1

    return {
        "task": "current-value recall under updates",
        "entities": n_entities,
        "updates_each": updates,
        "dilmun_accuracy": round(dil_correct / n_entities, 4),
        "vector_accuracy": round(vec_correct / n_entities, 4),
    }


# ---------------------------------------------------------------------------
# 2. determinism under insertion-order shuffles
# ---------------------------------------------------------------------------

def bench_determinism(n_entities=150, updates=4, shuffles=8):
    """Same facts, inserted in `shuffles` different random orders. A store is
    'stable' on a query if it returns the same answer across every order."""
    rng = random.Random(SEED + 1)
    base = []
    for e in range(n_entities):
        vals = [(rng.choice(CITIES), ts) for ts in range(1, updates + 1)]
        base.append((f"user{e}", vals))

    queries = [f"user{e}" for e in range(n_entities)]
    dil_answers = []
    vec_answers = []

    for s in range(shuffles):
        order = list(range(len(base)))
        # shuffle the *insertion order* of writes, keep timestamps intact
        writes = []
        for entity, vals in base:
            for v, ts in vals:
                writes.append((entity, v, ts))
        random.Random(SEED + 100 + s).shuffle(writes)

        dil = fresh_dilmun()
        vec = VectorMemory()
        for entity, v, ts in writes:
            dil.write_fact(entity, "city", v, timestamp=float(ts))
            vec.write_fact(entity, "city", v)

        dil_answers.append({q: (dil.query(entity=q, predicate="city")[0].value
                                 if dil.query(entity=q, predicate="city") else None)
                            for q in queries})
        vec_answers.append({q: vec.recall_value(q, "city") for q in queries})

    def stable_fraction(answers):
        stable = 0
        for q in queries:
            vals = {a[q] for a in answers}
            if len(vals) == 1:
                stable += 1
        return stable / len(queries)

    return {
        "task": "determinism under insertion-order shuffles",
        "queries": n_entities,
        "shuffles": shuffles,
        "dilmun_stable_fraction": round(stable_fraction(dil_answers), 4),
        "vector_stable_fraction": round(stable_fraction(vec_answers), 4),
    }


# ---------------------------------------------------------------------------
# 3. duplicate suppression under predicate paraphrase
# ---------------------------------------------------------------------------

def bench_dedup(n_entities=200):
    """Each entity states the SAME fact under 4 predicate paraphrases.
    Dilmun (+registry) collapses to one canonical fact; the vector store
    keeps all four as separate documents."""
    aliases = ["owns", "possesses", "has", "is owner of"]
    reg = PredicateRegistry().register("OWNS", *aliases)

    dil = fresh_dilmun(predicates=reg)
    vec = VectorMemory()
    for e in range(n_entities):
        entity = f"user{e}"
        for i, alias in enumerate(aliases):
            dil.write_fact(entity, alias, "Car", timestamp=float(i + 1))
            vec.write_fact(entity, alias, "Car")

    dil_facts = len(dil.get_context(limit=None))
    # top-4 redundancy: how many of the top-4 vector hits for one entity are
    # the same (entity, value) restated under a different predicate?
    hits = vec.top_k("user0 owns Car", k=4)
    redundant = sum(1 for h in hits if h["entity"] == "user0" and h["value"] == "Car")

    return {
        "task": "duplicate suppression under predicate paraphrase",
        "entities": n_entities,
        "aliases_per_fact": len(aliases),
        "dilmun_stored_facts": dil_facts,
        "vector_stored_facts": vec.distinct_stored(),
        "vector_top4_redundant_hits": redundant,
    }


# ---------------------------------------------------------------------------
# 4. latency
# ---------------------------------------------------------------------------

def bench_latency(n=2000, queries=500):
    rng = random.Random(SEED + 2)
    facts = [(f"user{rng.randint(0, n // 5)}", "city", rng.choice(CITIES))
             for _ in range(n)]

    dil = fresh_dilmun()
    t0 = time.perf_counter()
    for i, (e, p, v) in enumerate(facts):
        dil.write_fact(e, p, v, timestamp=float(i))
    dil_write = time.perf_counter() - t0

    vec = VectorMemory()
    t0 = time.perf_counter()
    for e, p, v in facts:
        vec.write_fact(e, p, v)
    vec.build_index()
    vec_write = time.perf_counter() - t0

    qs = [f"user{rng.randint(0, n // 5)}" for _ in range(queries)]

    t0 = time.perf_counter()
    for q in qs:
        dil.query(entity=q, predicate="city")
    dil_query = (time.perf_counter() - t0) / queries

    t0 = time.perf_counter()
    for q in qs:
        vec.recall_value(q, "city")
    vec_query = (time.perf_counter() - t0) / queries

    return {
        "task": "latency",
        "facts_written": n,
        "queries": queries,
        "dilmun_write_facts_per_sec": round(n / dil_write),
        "vector_write_facts_per_sec": round(n / vec_write),
        "dilmun_query_ms": round(dil_query * 1000, 3),
        "vector_query_ms": round(vec_query * 1000, 3),
    }


def main():
    results = [
        bench_current_value(),
        bench_determinism(),
        bench_dedup(),
        bench_latency(),
    ]
    print(json.dumps(results, indent=2))

    out = Path(__file__).parent / "results.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
