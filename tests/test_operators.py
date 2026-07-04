"""Tests for the formal properties the README claims of each operator:

    C — idempotent, deterministic, resolves by timestamp > confidence > order
    F — idempotent closure over expired / low-confidence facts
    comp — path composition, valid iff f1.v == f2.e
    retrieval — deterministic structured scoring
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from dilmun import (
    Fact,
    build_graph,
    canonicalize,
    compose,
    composable,
    degree_centrality,
    derive,
    forget,
    retrieve,
    score_facts,
)


def fact(entity, predicate, value, t, conf=1.0, seq=0, expires_at=None):
    return Fact(
        entity=entity, predicate=predicate, value=value,
        timestamp=t, confidence=conf, seq=seq, expires_at=expires_at,
    )


# ---------------------------------------------------------------------------
# C — canonicalization
# ---------------------------------------------------------------------------

def test_canonicalize_highest_timestamp_wins():
    m = [
        fact("user", "city", "Miami", t=100, seq=0),
        fact("user", "city", "Orlando", t=200, seq=1),
    ]
    result = canonicalize(m)
    assert len(result) == 1
    assert result[0].value == "Orlando"


def test_canonicalize_confidence_breaks_timestamp_tie():
    m = [
        fact("user", "city", "Miami", t=100, conf=0.5, seq=0),
        fact("user", "city", "Orlando", t=100, conf=0.9, seq=1),
    ]
    assert canonicalize(m)[0].value == "Orlando"


def test_canonicalize_insertion_order_is_final_tiebreak():
    m = [
        fact("user", "city", "Miami", t=100, conf=0.9, seq=0),
        fact("user", "city", "Orlando", t=100, conf=0.9, seq=1),
    ]
    assert canonicalize(m)[0].value == "Miami"


def test_canonicalize_is_idempotent():
    m = [
        fact("user", "city", "Miami", t=100, seq=0),
        fact("user", "city", "Orlando", t=200, seq=1),
        fact("user", "name", "Alice", t=150, seq=2),
    ]
    once = canonicalize(m)
    twice = canonicalize(once)
    assert once == twice


def test_canonicalize_is_deterministic():
    m1 = [
        fact("user", "city", "Miami", t=100, seq=0),
        fact("user", "city", "Orlando", t=200, seq=1),
    ]
    m2 = list(reversed(m1))  # same set, different iteration order
    assert canonicalize(m1) == canonicalize(m2)


def test_canonicalize_keeps_non_conflicting_facts():
    m = [
        fact("user", "city", "Miami", t=100, seq=0),
        fact("user", "name", "Alice", t=100, seq=1),
        fact("bot", "city", "Miami", t=100, seq=2),
    ]
    assert len(canonicalize(m)) == 3


# ---------------------------------------------------------------------------
# F — forgetting
# ---------------------------------------------------------------------------

def test_forget_removes_expired_facts():
    m = [
        fact("a", "p", "x", t=100, seq=0, expires_at=500),
        fact("b", "q", "y", t=100, seq=1),
    ]
    kept = forget(m, now=1000)
    assert [f.entity for f in kept] == ["b"]


def test_forget_removes_low_confidence_facts():
    m = [
        fact("a", "p", "x", t=100, conf=0.1, seq=0),
        fact("b", "q", "y", t=100, conf=0.9, seq=1),
    ]
    kept = forget(m, now=1000, min_confidence=0.5)
    assert [f.entity for f in kept] == ["b"]


def test_forget_is_idempotent():
    m = [
        fact("a", "p", "x", t=100, conf=0.1, seq=0, expires_at=500),
        fact("b", "q", "y", t=100, conf=0.9, seq=1),
        fact("b", "q", "z", t=200, conf=0.8, seq=2),
    ]
    once = forget(m, now=1000, min_confidence=0.5, contradiction_pressure=True)
    twice = forget(once, now=1000, min_confidence=0.5, contradiction_pressure=True)
    assert once == twice


def test_forget_contradiction_pressure():
    m = [
        fact("user", "city", "Miami", t=100, seq=0),
        fact("user", "city", "Orlando", t=200, seq=1),
        fact("user", "name", "Alice", t=100, seq=2),
    ]
    kept = forget(m, now=1000, contradiction_pressure=True)
    values = {f.value for f in kept}
    assert "Miami" not in values     # lost to Orlando with a different value
    assert {"Orlando", "Alice"} <= values


# ---------------------------------------------------------------------------
# comp — relational composition
# ---------------------------------------------------------------------------

def test_compose_readme_example():
    f1 = fact("A", "likes", "B", t=100, conf=0.9, seq=0)
    f2 = fact("B", "category", "C", t=200, conf=0.8, seq=1)
    assert composable(f1, f2)
    derived_fact = compose(f1, f2)
    assert (derived_fact.entity, derived_fact.predicate, derived_fact.value) == (
        "A", "likes_category", "C"
    )
    assert derived_fact.timestamp == 200
    assert abs(derived_fact.confidence - 0.72) < 1e-9
    assert derived_fact.derived_from == (f1.id, f2.id)


def test_compose_invalid_when_path_broken():
    f1 = fact("A", "likes", "B", t=100, seq=0)
    f2 = fact("X", "category", "C", t=200, seq=1)
    assert not composable(f1, f2)
    try:
        compose(f1, f2)
        assert False, "compose should reject non-adjacent facts"
    except ValueError:
        pass


def test_derive_finds_all_paths():
    m = [
        fact("Alice", "likes", "Coffee", t=100, seq=0),
        fact("Coffee", "served_at", "Cafe", t=100, seq=1),
        fact("Cafe", "located_in", "Miami", t=100, seq=2),
    ]
    derived_facts = derive(m)
    triples = {(f.entity, f.predicate, f.value) for f in derived_facts}
    assert ("Alice", "likes_served_at", "Cafe") in triples
    assert ("Coffee", "served_at_located_in", "Miami") in triples


# ---------------------------------------------------------------------------
# graph + retrieval
# ---------------------------------------------------------------------------

def test_build_graph():
    m = [
        fact("Alice", "likes", "Coffee", t=100, seq=0),
        fact("Coffee", "served_at", "Cafe", t=100, seq=1),
    ]
    graph = build_graph(m)
    assert graph == {
        "Alice": [("likes", "Coffee")],
        "Coffee": [("served_at", "Cafe")],
    }


def test_degree_centrality_normalized():
    m = [
        fact("Alice", "likes", "Coffee", t=100, seq=0),
        fact("Bob", "likes", "Coffee", t=100, seq=1),
    ]
    centrality = degree_centrality(m)
    assert centrality["Coffee"] == 1.0        # degree 2, the max
    assert centrality["Alice"] == 0.5


def test_scoring_and_retrieve_order():
    m = [
        fact("a", "p", "x", t=100, conf=0.1, seq=0),
        fact("b", "q", "y", t=200, conf=1.0, seq=1),
    ]
    scores = score_facts(m)
    assert scores[m[1].id] > scores[m[0].id]
    ranked = retrieve(m)
    assert ranked[0].entity == "b"
    assert retrieve(m, limit=1) == [ranked[0]]


def test_retrieve_is_deterministic():
    m = [
        fact("a", "p", "x", t=100, conf=0.5, seq=0),
        fact("b", "q", "y", t=100, conf=0.5, seq=1),
    ]
    assert retrieve(m) == retrieve(list(reversed(m)))


ALL_TESTS = [
    test_canonicalize_highest_timestamp_wins,
    test_canonicalize_confidence_breaks_timestamp_tie,
    test_canonicalize_insertion_order_is_final_tiebreak,
    test_canonicalize_is_idempotent,
    test_canonicalize_is_deterministic,
    test_canonicalize_keeps_non_conflicting_facts,
    test_forget_removes_expired_facts,
    test_forget_removes_low_confidence_facts,
    test_forget_is_idempotent,
    test_forget_contradiction_pressure,
    test_compose_readme_example,
    test_compose_invalid_when_path_broken,
    test_derive_finds_all_paths,
    test_build_graph,
    test_degree_centrality_normalized,
    test_scoring_and_retrieve_order,
    test_retrieve_is_deterministic,
]

if __name__ == "__main__":
    for test in ALL_TESTS:
        test()
        print(f"ok  {test.__name__}")
    print("All tests passed!")
