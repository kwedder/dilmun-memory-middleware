"""
Which mathematical framing has Dilmun actually earned?

Two candidate lenses were on the table:

  * rewrite system / abstract reduction system (ARS) — operators are
    reductions toward a normal form; the prize property is CONFLUENCE
    (different valid orders reach the same normal form).
  * join-semilattice / LWW-Map CRDT — the prize property is that MERGE
    obeys the semilattice laws (idempotent, commutative, associative).

This harness doesn't argue; it tests. Over many random memory states it
checks each property empirically and reports the fraction that hold, plus a
concrete counterexample when one fails. Seeded and reproducible:

    python benchmarks/algebra_properties.py
"""

from __future__ import annotations

import itertools
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dilmun import Fact, PredicateRegistry, canonicalize, forget, merge, normalize

SEED = 20260704
NOW = 10_000.0
MIN_CONF = 0.5          # an active confidence floor for the Forget policy

# predicate aliases that all normalize to one canonical predicate
ALIASES = ["owns", "possesses", "has", "is owner of"]
REG = PredicateRegistry().register("OWNS", *ALIASES)
PREDS = ALIASES + ["city", "likes"]          # some normalize/merge, some don't
VALUES = ["Miami", "Orlando", "Tampa", "Naples", "Ocala"]
ENTITIES = [f"user{i}" for i in range(6)]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def random_state(rng: random.Random, n: int) -> list:
    facts = []
    for seq in range(n):
        facts.append(Fact(
            entity=rng.choice(ENTITIES),
            predicate=rng.choice(PREDS),
            value=rng.choice(VALUES),
            timestamp=float(rng.randint(1, 50)),
            confidence=round(rng.uniform(0.0, 1.0), 3),
            seq=seq,
        ))
    return facts


def sig(state) -> frozenset:
    """Semantic signature: the set of (entity, predicate, value) triples.
    Two states with the same signature agree on *what is known*."""
    return frozenset((f.entity, f.predicate, f.value) for f in state)


# reduction operators as M -> M
def N(state):
    return normalize(state, REG)

def C(state):
    return canonicalize(state)

def F(state):
    return forget(state, now=NOW, min_confidence=MIN_CONF)


def to_fixpoint(state, schedule, max_rounds=50):
    """Apply the operators in `schedule` cyclically until the signature
    stops changing (the normal form under that reduction strategy)."""
    cur = list(state)
    last = sig(cur)
    for _ in range(max_rounds):
        for op in schedule:
            cur = op(cur)
        s = sig(cur)
        if s == last:
            return cur, s
        last = s
    return cur, sig(cur)


# ---------------------------------------------------------------------------
# property checks
# ---------------------------------------------------------------------------

def run(trials=3000, size=12):
    rng = random.Random(SEED)
    tallies = {
        "determinism_C": [0, 0],
        "idempotence_N": [0, 0],
        "idempotence_C": [0, 0],
        "idempotence_F": [0, 0],
        "confluence_NC": [0, 0],       # rewrite lens, core {N, C}
        "confluence_NCF": [0, 0],      # rewrite lens, full {N, C, F}
        "merge_idempotent": [0, 0],
        "merge_commutative": [0, 0],
        "merge_associative": [0, 0],
    }
    counterexamples = {}

    for _ in range(trials):
        M = random_state(rng, size)

        # determinism: canonicalize is invariant to input order
        shuffled = M[:]
        rng.shuffle(shuffled)
        ok = sig(C(M)) == sig(C(shuffled))
        _tally(tallies["determinism_C"], ok)

        # idempotence of each reducer
        _tally(tallies["idempotence_N"], sig(N(N(M))) == sig(N(M)))
        _tally(tallies["idempotence_C"], sig(C(C(M))) == sig(C(M)))
        _tally(tallies["idempotence_F"], sig(F(F(M))) == sig(F(M)))

        # confluence of the core reduction system {N, C}
        nc_outcomes = {to_fixpoint(M, sched)[1]
                       for sched in itertools.permutations([N, C])}
        ok_nc = len(nc_outcomes) == 1
        _tally(tallies["confluence_NC"], ok_nc)
        if not ok_nc and "confluence_NC" not in counterexamples:
            counterexamples["confluence_NC"] = _describe(M, [N, C])

        # confluence of the full reduction system {N, C, F}
        ncf_outcomes = {to_fixpoint(M, sched)[1]
                        for sched in itertools.permutations([N, C, F])}
        ok_ncf = len(ncf_outcomes) == 1
        _tally(tallies["confluence_NCF"], ok_ncf)
        if not ok_ncf and "confluence_NCF" not in counterexamples:
            counterexamples["confluence_NCF"] = _describe(M, [N, C, F])

        # merge / semilattice laws (compared on canonical signatures)
        A = random_state(rng, size // 2)
        B = random_state(rng, size // 2)
        Cc = random_state(rng, size // 2)
        _tally(tallies["merge_idempotent"], sig(merge(A, A)) == sig(C(A)))
        _tally(tallies["merge_commutative"], sig(merge(A, B)) == sig(merge(B, A)))
        _tally(tallies["merge_associative"],
               sig(merge(merge(A, B), Cc)) == sig(merge(A, merge(B, Cc))))

    report = {
        "seed": SEED, "trials": trials, "state_size": size,
        "min_confidence_floor": MIN_CONF,
        "properties": {k: round(v[0] / (v[0] + v[1]), 4) for k, v in tallies.items()},
        "counterexamples": counterexamples,
    }
    return report


def _tally(cell, ok):
    cell[0 if ok else 1] += 1


def _describe(M, ops):
    """Return the distinct normal forms an operator set produces, for a
    concrete failure witness."""
    outcomes = {}
    for sched in itertools.permutations(ops):
        order = "".join(op.__name__ for op in sched)
        _, s = to_fixpoint(M, sched)
        outcomes[order] = sorted(f"{e}.{p}={v}" for (e, p, v) in s)
    return outcomes


if __name__ == "__main__":
    report = run()
    print(json.dumps(report, indent=2))
    out = Path(__file__).parent / "algebra_results.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")
