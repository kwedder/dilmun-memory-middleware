"""Regression tests for the algebraic properties documented in MODEL.md.

These pin the two load-bearing findings from benchmarks/algebra_properties.py:
the {Normalize, Canonicalize} core is confluent, while adding Forget breaks
confluence (C and F do not commute). Also pins the semilattice merge laws.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from dilmun import (
    Fact,
    PredicateRegistry,
    canonicalize,
    forget,
    merge,
    normalize,
)

REG = PredicateRegistry().register("OWNS", "owns", "possesses", "has")


def fact(e, p, v, t, c=1.0, seq=0):
    return Fact(entity=e, predicate=p, value=v, timestamp=t, confidence=c, seq=seq)


def triples(state):
    return frozenset((f.entity, f.predicate, f.value) for f in state)


# ---------------------------------------------------------------------------
# core {N, C} is confluent — order of Normalize and Canonicalize does not
# change the canonical normal form
# ---------------------------------------------------------------------------

def test_core_NC_is_confluent():
    m = [
        fact("A", "owns", "Miami", t=3, seq=0),
        fact("A", "possesses", "Orlando", t=5, seq=1),   # newer, different alias
        fact("A", "has", "Tampa", t=4, seq=2),
    ]
    N = lambda s: normalize(s, REG)
    C = canonicalize

    nc = triples(C(N(m)))
    cn = triples(N(C(m)))          # after C, still need N to collapse predicates
    cnc = triples(C(N(C(m))))      # run to fixpoint
    assert nc == cnc
    # N-first already at fixpoint; C-first needs one more C, but the KNOWLEDGE
    # (entity, predicate, value) converges to the single newest fact:
    assert nc == frozenset({("A", "OWNS", "Orlando")})


# ---------------------------------------------------------------------------
# {N, C, F} is NOT confluent — C and F do not commute (MODEL.md §5 witness)
# ---------------------------------------------------------------------------

def test_canonicalize_and_forget_do_not_commute():
    m = [
        fact("user", "city", "X", t=9, c=0.2, seq=0),      # newest, low confidence
        fact("user", "city", "Tampa", t=1, c=0.9, seq=1),  # older, confident
    ]
    C = canonicalize
    F = lambda s: forget(s, now=100.0, min_confidence=0.5)

    c_then_f = triples(F(C(m)))   # C keeps X (newest); F deletes X (c<0.5)
    f_then_c = triples(C(F(m)))   # F deletes X; C keeps Tampa

    assert c_then_f == frozenset()                              # city forgotten
    assert f_then_c == frozenset({("user", "city", "Tampa")})   # city = Tampa
    assert c_then_f != f_then_c                                 # non-confluent


# ---------------------------------------------------------------------------
# merge is a semilattice join (idempotent, commutative, associative)
# ---------------------------------------------------------------------------

def test_merge_semilattice_laws():
    A = [fact("u", "city", "Miami", t=1, seq=0)]
    B = [fact("u", "city", "Orlando", t=2, seq=1)]
    Cc = [fact("u", "name", "Alice", t=1, seq=2)]

    assert triples(merge(A, A)) == triples(canonicalize(A))          # idempotent
    assert triples(merge(A, B)) == triples(merge(B, A))              # commutative
    assert triples(merge(merge(A, B), Cc)) == triples(merge(A, merge(B, Cc)))  # assoc


ALL_TESTS = [
    test_core_NC_is_confluent,
    test_canonicalize_and_forget_do_not_commute,
    test_merge_semilattice_laws,
]

if __name__ == "__main__":
    for t in ALL_TESTS:
        t()
        print(f"ok  {t.__name__}")
    print("All tests passed!")
