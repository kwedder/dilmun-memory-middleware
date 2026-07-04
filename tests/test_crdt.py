"""Tests for the distributed LWW-Map CRDT layer (dilmun/crdt.py).

Covers the two properties that distinguish a genuine multi-replica CvRDT from
the single-store merge: replica-consistent convergence under reordering, and
tombstone-based removal with no resurrection — plus the semilattice laws with
the global (id-based) tie-break.
"""

import random
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from dilmun import Fact, LWWMap, merge_all


def fact(e, p, v, t, c=1.0, fid=None):
    return Fact(entity=e, predicate=p, value=v, timestamp=t, confidence=c,
                id=fid or f"{e}-{p}-{v}-{t}")


# ---------------------------------------------------------------------------
# semilattice laws with the global tie-break
# ---------------------------------------------------------------------------

def test_merge_semilattice_laws_global_order():
    A = LWWMap.from_facts([fact("u", "city", "Miami", t=1)])
    B = LWWMap.from_facts([fact("u", "city", "Orlando", t=2)])
    Cc = LWWMap.from_facts([fact("u", "name", "Alice", t=1)])

    assert A.merge(A) == A                                   # idempotent
    assert A.merge(B).signature() == B.merge(A).signature()  # commutative
    assert (A.merge(B).merge(Cc)).signature() == (A.merge(B.merge(Cc))).signature()


def test_latest_timestamp_wins():
    m = (LWWMap()
         .put(fact("u", "city", "Miami", t=1))
         .put(fact("u", "city", "Orlando", t=2)))
    assert m.get("u", "city").value == "Orlando"


def test_tie_broken_consistently_by_id():
    # same timestamp and confidence: the winner is decided by id, which is
    # identical on every replica, so both orders agree.
    f1 = fact("u", "city", "Miami", t=5, c=0.9, fid="aaa")
    f2 = fact("u", "city", "Orlando", t=5, c=0.9, fid="zzz")
    ab = LWWMap().put(f1).put(f2)
    ba = LWWMap().put(f2).put(f1)
    assert ab.get("u", "city").value == ba.get("u", "city").value


# ---------------------------------------------------------------------------
# convergence: replicas that saw the same ops in any order agree
# ---------------------------------------------------------------------------

def test_replicas_converge_under_reordering():
    ops = [
        fact("u1", "city", "Miami", t=1),
        fact("u1", "city", "Orlando", t=3),
        fact("u1", "city", "Tampa", t=2),
        fact("u2", "name", "Alice", t=1),
        fact("u2", "name", "Alicia", t=4),
        fact("u3", "likes", "Coffee", t=2),
    ]
    signatures = set()
    for seed in range(12):
        shuffled = ops[:]
        random.Random(seed).shuffle(shuffled)
        # each "replica" absorbs the ops in its own order
        replica = LWWMap.from_facts(shuffled)
        signatures.add(replica.signature())
    assert len(signatures) == 1                       # all replicas converged
    conv = next(iter(signatures))
    assert ("u1", "city", "Orlando") in conv          # newest city (t=3)
    assert ("u2", "name", "Alicia") in conv           # newest name (t=4)


def test_gossip_partial_merges_converge():
    a = LWWMap.from_facts([fact("u", "city", "Miami", t=1)])
    b = LWWMap.from_facts([fact("u", "city", "Orlando", t=3)])
    c = LWWMap.from_facts([fact("u", "city", "Tampa", t=2)])
    # different merge topologies reach the same state
    left = a.merge(b).merge(c)
    right = c.merge(a).merge(b)
    star = merge_all([b, a, c])
    assert left.signature() == right.signature() == star.signature()
    assert left.get("u", "city").value == "Orlando"


# ---------------------------------------------------------------------------
# tombstones: removal is CRDT-safe (no resurrection)
# ---------------------------------------------------------------------------

def test_dominating_delete_is_not_resurrected():
    holds = LWWMap.from_facts([fact("u", "city", "Miami", t=1)])
    deletes = LWWMap().remove("u", "city", timestamp=2)   # delete after the put
    merged = holds.merge(deletes)
    assert merged.get("u", "city") is None                # stays deleted
    assert merged.signature() == frozenset()


def test_delete_loses_to_newer_put():
    deletes = LWWMap().remove("u", "city", timestamp=2)
    newer = LWWMap.from_facts([fact("u", "city", "Orlando", t=3)])  # written after delete
    merged = deletes.merge(newer)
    assert merged.get("u", "city").value == "Orlando"     # re-added by newer write


def test_delete_wins_same_timestamp_tie():
    holds = LWWMap.from_facts([fact("u", "city", "Miami", t=5)])
    deletes = LWWMap().remove("u", "city", timestamp=5)   # tie
    assert holds.merge(deletes).get("u", "city") is None  # delete wins the tie


def test_delete_convergence_regardless_of_order():
    put = LWWMap.from_facts([fact("u", "city", "Miami", t=1)])
    rm = LWWMap().remove("u", "city", timestamp=2)
    readd = LWWMap.from_facts([fact("u", "city", "Orlando", t=3)])
    a = put.merge(rm).merge(readd)
    b = readd.merge(put).merge(rm)
    assert a.signature() == b.signature()
    assert a.get("u", "city").value == "Orlando"          # newest op is the re-add


ALL_TESTS = [
    test_merge_semilattice_laws_global_order,
    test_latest_timestamp_wins,
    test_tie_broken_consistently_by_id,
    test_replicas_converge_under_reordering,
    test_gossip_partial_merges_converge,
    test_dominating_delete_is_not_resurrected,
    test_delete_loses_to_newer_put,
    test_delete_wins_same_timestamp_tie,
    test_delete_convergence_regardless_of_order,
]

if __name__ == "__main__":
    for t in ALL_TESTS:
        t()
        print(f"ok  {t.__name__}")
    print("All tests passed!")
