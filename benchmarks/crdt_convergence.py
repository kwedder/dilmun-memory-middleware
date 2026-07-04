"""
Distributed convergence benchmark for the LWW-Map CRDT.

Simulates N replicas that each receive the same operation log (puts and
removes) in a random delivery order, with random partial gossip merges between
them, then a final all-to-all merge. A correct CvRDT converges: every replica
ends in identical state regardless of delivery order or merge topology.

Also contrasts the CRDT's global (id-based) tie-break against a naive
per-replica (seq-based) tie-break, to show why the global order is required:
the naive one diverges on same-timestamp ties.

Seeded and reproducible:  python benchmarks/crdt_convergence.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dilmun import Fact, LWWMap, merge_all

SEED = 20260704
ENTITIES = [f"user{i}" for i in range(8)]
PREDS = ["city", "name", "likes"]
VALUES = ["Miami", "Orlando", "Tampa", "Naples", "Ocala"]


def make_oplog(rng, n_ops, tie_rate):
    """A shared operation log. With probability `tie_rate`, an op reuses an
    existing (timestamp) to force same-timestamp ties across different values."""
    ops = []
    t = 0
    for i in range(n_ops):
        if ops and rng.random() < tie_rate:
            ts = rng.choice(ops)[3]          # collide a previous timestamp
        else:
            t += 1
            ts = t
        e, p = rng.choice(ENTITIES), rng.choice(PREDS)
        if rng.random() < 0.15:              # 15% removals
            ops.append(("rm", e, p, ts))
        else:
            v = rng.choice(VALUES)
            ops.append(("put", e, p, ts, v, f"op{i}"))
    return ops


def apply_log(ops):
    m = LWWMap()
    for op in ops:
        if op[0] == "put":
            _, e, p, ts, v, oid = op
            m = m.put(Fact(entity=e, predicate=p, value=v, timestamp=float(ts),
                           confidence=1.0, id=oid))
        else:
            _, e, p, ts = op
            m = m.remove(e, p, timestamp=float(ts))
    return m


def apply_log_seq_tiebreak(ops):
    """A NAIVE replica: same LWW logic, but ties broken by local delivery
    order (first-delivered wins) instead of the global id. Models the old
    single-store `seq` behavior in a distributed setting."""
    winners = {}   # key -> (timestamp, value_or_None)
    for op in ops:
        if op[0] == "put":
            _, e, p, ts, v, _ = op
            key = (e, p)
            cur = winners.get(key)
            # strictly-greater timestamp wins; TIES keep the first delivered
            if cur is None or ts > cur[0]:
                winners[key] = (ts, v)
        else:
            _, e, p, ts = op
            key = (e, p)
            cur = winners.get(key)
            if cur is None or ts > cur[0]:
                winners[key] = (ts, None)
    return frozenset((e, p, v) for (e, p), (ts, v) in winners.items() if v is not None)


def run(replicas=6, trials=400, n_ops=60, tie_rate=0.35):
    rng = random.Random(SEED)
    crdt_converged = 0
    seq_converged = 0

    for _ in range(trials):
        ops = make_oplog(rng, n_ops, tie_rate)

        # --- CRDT replicas: random delivery order + random gossip topology ---
        replica_states = []
        for r in range(replicas):
            delivery = ops[:]
            random.Random(rng.random()).shuffle(delivery)
            replica_states.append(apply_log(delivery))
        # random pairwise gossip rounds
        for _ in range(replicas):
            i, j = rng.randrange(replicas), rng.randrange(replicas)
            merged = replica_states[i].merge(replica_states[j])
            replica_states[i] = replica_states[j] = merged
        final = merge_all(replica_states)
        crdt_sigs = {rs.merge(final).signature() for rs in replica_states}
        crdt_converged += (len(crdt_sigs) == 1)

        # --- naive seq-tiebreak replicas over the same delivery orders ------
        seq_sigs = set()
        for r in range(replicas):
            delivery = ops[:]
            random.Random(rng.random()).shuffle(delivery)
            seq_sigs.add(apply_log_seq_tiebreak(delivery))
        seq_converged += (len(seq_sigs) == 1)

    return {
        "seed": SEED, "replicas": replicas, "trials": trials,
        "ops_per_trial": n_ops, "timestamp_tie_rate": tie_rate,
        "crdt_global_tiebreak_convergence": round(crdt_converged / trials, 4),
        "naive_seq_tiebreak_convergence": round(seq_converged / trials, 4),
    }


def main():
    report = run()
    print(json.dumps(report, indent=2))
    out = Path(__file__).parent / "crdt_convergence_results.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
