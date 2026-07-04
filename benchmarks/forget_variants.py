"""
Research branch: can a confidence-aware Forget restore confluence, and should
it be the default?

Evaluated on two axes, per the review:

  1. Algebraic — does the variant make {N, C, F} confluent while keeping
     idempotence?
  2. Semantic — does the resulting memory match the intended "trust, then take
     the latest" behavior?

The experiment tests three designs of Forget:

  F_global   remove every fact below the confidence floor            (current)
  F_ranked   per (e,p): drop failing facts if any pass; else keep the
             newest as a fallback so a key is never wholly lost
  (K)        no new Forget at all — treat the reducer as the COMPOSITE
             K = C ∘ F (filter, then canonicalize) applied in fixed order

Seeded and reproducible:  python benchmarks/forget_variants.py
"""

from __future__ import annotations

import itertools
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dilmun import Fact, PredicateRegistry, canonicalize, normalize

SEED = 20260704
FLOOR = 0.5
REG = PredicateRegistry().register("OWNS", "owns", "possesses", "has")
PREDS = ["owns", "possesses", "has", "city", "likes"]
VALUES = ["Miami", "Orlando", "Tampa", "Naples", "Ocala"]
ENTITIES = [f"user{i}" for i in range(6)]


def random_state(rng, n):
    return [Fact(entity=rng.choice(ENTITIES), predicate=rng.choice(PREDS),
                 value=rng.choice(VALUES), timestamp=float(rng.randint(1, 50)),
                 confidence=round(rng.uniform(0.0, 1.0), 3), seq=i)
            for i in range(n)]


def sig(state):
    return frozenset((f.entity, f.predicate, f.value) for f in state)


def N(s):
    return normalize(s, REG)

def C(s):
    return canonicalize(s)

def F_global(s):
    return [f for f in s if f.confidence >= FLOOR]

def F_ranked(s):
    groups = defaultdict(list)
    for f in s:
        groups[(f.entity, f.predicate)].append(f)
    out = []
    for group in groups.values():
        passing = [f for f in group if f.confidence >= FLOOR]
        if passing:
            out.extend(passing)
        else:  # keep newest as fallback so the key is not wholly lost
            out.append(max(group, key=lambda f: (f.timestamp, f.confidence, -f.seq)))
    return out


def intended_strict(s):
    """Per (e,p): the newest fact passing the floor; empty if none.
    This is exactly what C(F_global(M)) computes."""
    groups = defaultdict(list)
    for f in N(s):
        if f.confidence >= FLOOR:
            groups[(f.entity, f.predicate)].append(f)
    return frozenset((e, p, max(g, key=lambda f: (f.timestamp, f.confidence, -f.seq)).value)
                     for (e, p), g in groups.items())


def to_fixpoint(state, schedule, max_rounds=50):
    cur, last = list(state), sig(list(state))
    for _ in range(max_rounds):
        for op in schedule:
            cur = op(cur)
        s = sig(cur)
        if s == last:
            return s
        last = s
    return sig(cur)


def confluence(reducers, trials, size, rng):
    ok = 0
    for _ in range(trials):
        M = random_state(rng, size)
        outcomes = {to_fixpoint(M, sched) for sched in itertools.permutations(reducers)}
        ok += (len(outcomes) == 1)
    return round(ok / trials, 4)


def composite_check(F, trials, size, rng):
    """K = C ∘ F: measure idempotence and match to intended_strict semantics."""
    idem = match = 0
    for _ in range(trials):
        M = random_state(rng, size)
        K = lambda s: C(F(N(s)))
        k = K(M)
        idem += (sig(K(k)) == sig(k))
        match += (sig(k) == intended_strict(M))
    return round(idem / trials, 4), round(match / trials, 4)


def main():
    T, S = 3000, 12
    r = random.Random

    results = {
        "seed": SEED, "trials": T, "state_size": S, "confidence_floor": FLOOR,
        "algebraic_axis": {
            "confluence_{N,C,F_global}": confluence([N, C, F_global], T, S, r(SEED)),
            "confluence_{N,C,F_ranked}": confluence([N, C, F_ranked], T, S, r(SEED)),
        },
        "composite_reducer_K": {},
        "semantic_axis": {},
    }

    idem_g, match_g = composite_check(F_global, T, S, r(SEED))
    idem_r, match_r = composite_check(F_ranked, T, S, r(SEED))
    results["composite_reducer_K"] = {
        "K=C∘F_global_idempotent": idem_g,
        "K=C∘F_ranked_idempotent": idem_r,
    }
    results["semantic_axis"] = {
        "K=C∘F_global_matches_intended_strict": match_g,
        "K=C∘F_ranked_matches_intended_strict": match_r,
    }

    print(json.dumps(results, indent=2))
    out = Path(__file__).parent / "forget_variants_results.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
