"""Tests for predicate normalization and the merge operator."""

import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from dilmun import (
    DilmunMemory,
    Fact,
    PredicateRegistry,
    canonicalize,
    default_normalize,
    merge,
    normalize,
)


def fact(entity, predicate, value, t, conf=1.0, seq=0):
    return Fact(entity=entity, predicate=predicate, value=value,
                timestamp=t, confidence=conf, seq=seq)


# ---------------------------------------------------------------------------
# default normalization
# ---------------------------------------------------------------------------

def test_default_normalize_forms():
    assert default_normalize("is owner of") == "is_owner_of"
    assert default_normalize("Favorite  Color") == "favorite_color"
    assert default_normalize("served-at") == "served_at"
    assert default_normalize("  HAS  ") == "has"


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------

def test_registry_collapses_aliases():
    reg = PredicateRegistry().register("OWNS", "owns", "possesses", "has", "is owner of")
    assert reg.normalize("possesses") == "OWNS"
    assert reg.normalize("is owner of") == "OWNS"
    assert reg.normalize("HAS") == "OWNS"


def test_registry_passes_through_unknown():
    reg = PredicateRegistry().register("OWNS", "owns")
    assert reg.normalize("likes") == "likes"          # default form, unmerged
    assert reg.normalize("is friends with") == "is_friends_with"


def test_normalize_operator_merges_fragmented_facts():
    reg = PredicateRegistry().register("OWNS", "owns", "possesses", "has")
    m = [
        fact("A", "owns", "B", t=100, seq=0),
        fact("A", "possesses", "B", t=200, seq=1),
        fact("A", "has", "B", t=300, seq=2),
    ]
    # Before normalization: three distinct predicates, no conflict to resolve.
    assert len(canonicalize(m)) == 3
    # After normalization: one predicate, one value -> collapses to one fact.
    collapsed = canonicalize(normalize(m, reg))
    assert len(collapsed) == 1
    assert collapsed[0].predicate == "OWNS"


def test_normalize_preserves_fact_identity():
    reg = PredicateRegistry().register("OWNS", "owns")
    f = fact("A", "owns", "B", t=100, seq=3)
    out = normalize([f], reg)[0]
    assert out.id == f.id
    assert out.seq == f.seq
    assert out.timestamp == f.timestamp
    assert out.predicate == "OWNS"


# ---------------------------------------------------------------------------
# normalization through DilmunMemory
# ---------------------------------------------------------------------------

def test_memory_write_time_normalization():
    reg = PredicateRegistry().register("OWNS", "owns", "possesses", "has")
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = DilmunMemory(tmpdir, predicates=reg)
        memory.write_fact("A", "owns", "Car", timestamp=100.0)
        memory.write_fact("A", "possesses", "Car", timestamp=200.0)
        memory.write_fact("A", "has", "Car", timestamp=300.0)

        context = memory.get_context()
        assert len(context) == 1
        assert context[0].predicate == "OWNS"


def test_memory_default_normalization_without_registry():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = DilmunMemory(tmpdir)
        f = memory.write_fact("user", "Favorite Color", "blue")
        assert f.predicate == "favorite_color"


# ---------------------------------------------------------------------------
# merge operator
# ---------------------------------------------------------------------------

def test_merge_canonicalizes_across_states():
    m1 = [fact("user", "city", "Miami", t=100, seq=0)]
    m2 = [fact("user", "city", "Orlando", t=200, seq=1)]
    merged = merge(m1, m2)
    assert len(merged) == 1
    assert merged[0].value == "Orlando"


def test_merge_is_commutative():
    m1 = [fact("user", "city", "Miami", t=100, seq=0),
          fact("user", "name", "Alice", t=100, seq=2)]
    m2 = [fact("user", "city", "Orlando", t=200, seq=1)]
    a = merge(m1, m2)
    b = merge(m2, m1)
    assert a == b


def test_merge_is_associative():
    a = [fact("user", "city", "Miami", t=100, seq=0)]
    b = [fact("user", "city", "Orlando", t=200, seq=1)]
    c = [fact("user", "city", "Tampa", t=150, seq=2)]
    left = merge(merge(a, b), c)
    right = merge(a, merge(b, c))
    assert left == right
    assert left[0].value == "Orlando"  # highest timestamp wins regardless


def test_merge_deduplicates_by_id():
    f = fact("user", "name", "Alice", t=100, seq=0)
    merged = merge([f], [f])
    assert len(merged) == 1


def test_memory_merge_two_stores():
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        a = DilmunMemory(d1)
        b = DilmunMemory(d2)
        a.write_fact("user", "city", "Miami", timestamp=100.0)
        b.write_fact("user", "city", "Orlando", timestamp=200.0)
        merged = a.merge(b)
        assert len(merged) == 1
        assert merged[0].value == "Orlando"


ALL_TESTS = [
    test_default_normalize_forms,
    test_registry_collapses_aliases,
    test_registry_passes_through_unknown,
    test_normalize_operator_merges_fragmented_facts,
    test_normalize_preserves_fact_identity,
    test_memory_write_time_normalization,
    test_memory_default_normalization_without_registry,
    test_merge_canonicalizes_across_states,
    test_merge_is_commutative,
    test_merge_is_associative,
    test_merge_deduplicates_by_id,
    test_memory_merge_two_stores,
]

if __name__ == "__main__":
    for test in ALL_TESTS:
        test()
        print(f"ok  {test.__name__}")
    print("All tests passed!")
