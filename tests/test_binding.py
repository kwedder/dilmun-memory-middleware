"""Tests for the draft clique-binding memory (dilmun/binding.py).

Covers the two operations it exists to provide, plus determinism:

    reconstruct  — recover missing (predicate, value) cells from present ones
    veridicality — accept genuine bundles; reject novel values AND novel
                   combinations of seen values (ghost memories)
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from dilmun import Fact
from dilmun.binding import BindingMemory


def record(mem, **cells):
    """Store one record from predicate=value kwargs."""
    mem.store_record(list(cells.items()))


# ---------------------------------------------------------------------------
# R1 — reconstruction
# ---------------------------------------------------------------------------

def test_reconstruct_recovers_missing_cell_from_known():
    mem = BindingMemory()
    record(mem, color="blue", shape="round", size="small")
    got = mem.reconstruct({"color": "blue", "shape": "round"}, ["size"])
    assert got == {"size": "small"}


def test_reconstruct_abstains_when_binding_incomplete():
    # two records share no full clique with the query -> honest None
    mem = BindingMemory()
    record(mem, color="blue", shape="round", size="small")
    record(mem, color="red", shape="square", size="large")
    # 'blue' + 'square' never co-occurred, so no value is bound to both
    got = mem.reconstruct({"color": "blue", "shape": "square"}, ["size"])
    assert got == {"size": None}


def test_reconstruct_disambiguates_by_binding():
    mem = BindingMemory()
    record(mem, color="blue", shape="round", size="small")
    record(mem, color="blue", shape="square", size="large")
    # blue+round -> small ; blue+square -> large
    assert mem.reconstruct({"color": "blue", "shape": "round"}, ["size"]) == {"size": "small"}
    assert mem.reconstruct({"color": "blue", "shape": "square"}, ["size"]) == {"size": "large"}


# ---------------------------------------------------------------------------
# R2 — veridicality / confabulation guard
# ---------------------------------------------------------------------------

def test_accepts_genuine_stored_bundle():
    mem = BindingMemory()
    record(mem, color="blue", shape="round", size="small")
    assert mem.is_genuine([("color", "blue"), ("shape", "round"), ("size", "small")])
    assert mem.veridicality([("color", "blue"), ("shape", "round"), ("size", "small")]) == 1.0


def test_rejects_novel_value():
    mem = BindingMemory()
    record(mem, color="blue", shape="round", size="small")
    # 'green' was never stored for color
    assert not mem.is_genuine([("color", "green"), ("shape", "round"), ("size", "small")])
    assert mem.veridicality([("color", "green"), ("shape", "round")]) == 0.0


def test_rejects_ghost_recombination():
    # every value is real, but this combination was never stored together
    mem = BindingMemory()
    record(mem, color="blue", shape="round", size="small")
    record(mem, color="red", shape="square", size="large")
    ghost = [("color", "blue"), ("shape", "square"), ("size", "large")]
    assert mem.veridicality(ghost) < 1.0
    assert not mem.is_genuine(ghost)


def test_veridicality_is_graded():
    mem = BindingMemory()
    record(mem, color="blue", shape="round", size="small")
    record(mem, color="blue", shape="round", size="large")  # blue+round shared
    # blue-round bound; blue-large & round-large bound; but this exact trio:
    partial = [("color", "blue"), ("shape", "round"), ("size", "large")]
    v = mem.veridicality(partial)
    assert 0.0 < v <= 1.0


# ---------------------------------------------------------------------------
# Fact integration + determinism
# ---------------------------------------------------------------------------

def test_store_facts_groups_by_entity_episode():
    mem = BindingMemory()
    facts = [
        Fact(entity="obj1", predicate="color", value="blue", timestamp=1.0, episode="e1"),
        Fact(entity="obj1", predicate="shape", value="round", timestamp=1.0, episode="e1"),
        Fact(entity="obj2", predicate="color", value="red", timestamp=2.0, episode="e1"),
        Fact(entity="obj2", predicate="shape", value="square", timestamp=2.0, episode="e1"),
    ]
    mem.store_facts(facts)
    assert mem.num_records == 2
    assert mem.is_genuine([("color", "blue"), ("shape", "round")])
    assert not mem.is_genuine([("color", "blue"), ("shape", "square")])  # cross-entity ghost


def test_deterministic_repeat():
    facts = [
        Fact(entity="o", predicate="a", value=str(i % 3), timestamp=float(i), episode="e")
        for i in range(6)
    ]
    m1, m2 = BindingMemory(), BindingMemory()
    m1.store_facts(facts)
    m2.store_facts(list(reversed(facts)))
    q = [("a", "0")]
    assert m1.veridicality(q) == m2.veridicality(q)
    assert m1.reconstruct({}, ["a"]) == m2.reconstruct({}, ["a"])
