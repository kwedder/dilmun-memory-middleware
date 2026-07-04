"""Tests for DilmunMemory: the README Quick Start, episode partitioning,
promotion, retrieval, and both storage backends."""

import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from dilmun import DilmunMemory, Fact


def test_readme_quick_start():
    """The Quick Start from the README, verbatim."""
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = DilmunMemory(tmpdir)

        memory.open_episode("chat_001")

        memory.write_fact(
            entity="user",
            predicate="favorite_color",
            value="blue",
            confidence=0.95,
        )

        memory.write_fact(
            entity="user",
            predicate="location",
            value="Miami",
        )

        context = memory.get_context()

        memory.close_episode()

        assert len(context) == 2
        by_predicate = {f.predicate: f for f in context}
        assert by_predicate["favorite_color"].value == "blue"
        assert by_predicate["favorite_color"].confidence == 0.95
        assert by_predicate["location"].value == "Miami"


def test_facts_are_immutable():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = DilmunMemory(tmpdir)
        fact = memory.write_fact("user", "name", "Alice")
        try:
            fact.value = "Bob"
            assert False, "Fact should be frozen"
        except AttributeError:
            pass


def test_updates_append_new_facts():
    """Updates create new facts, not mutations; retrieval sees the canonical one."""
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = DilmunMemory(tmpdir)
        memory.write_fact("user", "city", "Miami", timestamp=100.0)
        memory.write_fact("user", "city", "Orlando", timestamp=200.0)

        assert len(memory.facts()) == 2  # both facts still exist
        context = memory.get_context()
        assert len(context) == 1  # but only one is canonical
        assert context[0].value == "Orlando"


def test_episode_isolation():
    """Episode facts are isolated by default; global M_0 is always visible."""
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = DilmunMemory(tmpdir)
        memory.write_fact("user", "name", "Alice")  # global M_0

        memory.open_episode("ep_1")
        memory.write_fact("user", "mood", "happy")
        memory.close_episode()

        memory.open_episode("ep_2")
        memory.write_fact("user", "task", "write tests")
        predicates = {f.predicate for f in memory.get_context()}
        memory.close_episode()

        assert "name" in predicates       # global visible
        assert "task" in predicates       # active episode visible
        assert "mood" not in predicates   # other episode NOT visible


def test_explicit_promotion():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = DilmunMemory(tmpdir)
        memory.open_episode("ep_1")
        fact = memory.write_fact("user", "timezone", "EST")
        memory.close_episode()

        # Not visible outside its episode until promoted.
        assert memory.query(predicate="timezone") == []
        promoted = memory.promote(fact)
        assert promoted.episode is None
        assert memory.query(predicate="timezone")[0].value == "EST"


def test_retrieval_is_scored_and_limited():
    """score(f) = w1·ν + w2·recency + w3·centrality — higher wins."""
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = DilmunMemory(tmpdir)
        memory.write_fact("a", "p", "x", confidence=0.1, timestamp=100.0)
        memory.write_fact("b", "q", "y", confidence=1.0, timestamp=200.0)

        context = memory.get_context(limit=1)
        assert len(context) == 1
        assert context[0].entity == "b"  # newer and more confident


def test_graph_and_neighbors():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = DilmunMemory(tmpdir)
        memory.write_fact("Alice", "likes", "Coffee")
        memory.write_fact("Coffee", "served_at", "Cafe")

        graph = memory.graph()
        assert graph["Alice"] == [("likes", "Coffee")]
        assert memory.neighbors("Coffee") == [("served_at", "Cafe")]


def test_memory_forget_is_idempotent():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = DilmunMemory(tmpdir)
        memory.write_fact("user", "temp", "x", confidence=0.05)
        memory.write_fact("user", "name", "Alice", confidence=0.9)

        removed = memory.forget(min_confidence=0.5, now=1000.0)
        assert removed == 1
        removed_again = memory.forget(min_confidence=0.5, now=1000.0)
        assert removed_again == 0
        assert len(memory.facts()) == 1


def test_persistence_across_reopen_json():
    _check_persistence(backend="json")


def test_persistence_across_reopen_sqlite():
    _check_persistence(backend="sqlite")


def _check_persistence(backend: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = DilmunMemory(tmpdir, backend=backend)
        memory.open_episode("ep_1")
        memory.write_fact("user", "name", "Alice", confidence=0.9)
        memory.close_episode()
        memory.close()

        reopened = DilmunMemory(tmpdir, backend=backend)
        facts = reopened.facts(episode="ep_1")
        assert len(facts) == 1
        assert facts[0].value == "Alice"
        assert facts[0].confidence == 0.9
        assert "ep_1" in reopened.episodes()
        reopened.close()


def test_backends_agree():
    """Same writes through either backend yield the same canonical context."""
    results = {}
    for backend in ("json", "sqlite"):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = DilmunMemory(tmpdir, backend=backend)
            memory.write_fact("user", "city", "Miami", timestamp=100.0)
            memory.write_fact("user", "city", "Orlando", timestamp=200.0)
            memory.write_fact("user", "name", "Alice", timestamp=150.0)
            results[backend] = [
                (f.entity, f.predicate, f.value) for f in memory.get_context()
            ]
            memory.close()
    assert results["json"] == results["sqlite"]


def test_compose_and_derive_through_memory():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = DilmunMemory(tmpdir)
        f1 = memory.write_fact("Alice", "likes", "Coffee")
        f2 = memory.write_fact("Coffee", "category", "Beverage")

        derived = memory.compose(f1, f2)
        assert (derived.entity, derived.predicate, derived.value) == (
            "Alice", "likes_category", "Beverage"
        )

        all_derived = memory.derive(write=True)
        assert any(f.predicate == "likes_category" for f in all_derived)
        assert memory.query(predicate="likes_category")[0].value == "Beverage"


ALL_TESTS = [
    test_readme_quick_start,
    test_facts_are_immutable,
    test_updates_append_new_facts,
    test_episode_isolation,
    test_explicit_promotion,
    test_retrieval_is_scored_and_limited,
    test_graph_and_neighbors,
    test_memory_forget_is_idempotent,
    test_persistence_across_reopen_json,
    test_persistence_across_reopen_sqlite,
    test_backends_agree,
    test_compose_and_derive_through_memory,
]

if __name__ == "__main__":
    for test in ALL_TESTS:
        test()
        print(f"ok  {test.__name__}")
    print("All tests passed!")
