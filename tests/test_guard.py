"""Tests for the draft VeridicalityGuard (dilmun/guard.py).

The guard is a read-side confabulation gate over a memory's co-occurrence
structure. It must:
  * accept attested claims / bundles
  * reject novel values AND ghost recombinations
  * abstain (None) rather than confabulate on unanswerable reconstructions
  * gate a proposed (RAG-style) answer through the veridicality check
  * integrate with a live DilmunMemory without mutating it
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from dilmun import DilmunMemory, Fact
from dilmun.binding import BindingMemory
from dilmun.guard import VeridicalityGuard, Verdict


def facts_two_objects():
    # obj1 = (blue, round, small) ; obj2 = (red, square, large)
    return [
        Fact(entity="obj1", predicate="color", value="blue", timestamp=1.0),
        Fact(entity="obj1", predicate="shape", value="round", timestamp=1.0),
        Fact(entity="obj1", predicate="size", value="small", timestamp=1.0),
        Fact(entity="obj2", predicate="color", value="red", timestamp=2.0),
        Fact(entity="obj2", predicate="shape", value="square", timestamp=2.0),
        Fact(entity="obj2", predicate="size", value="large", timestamp=2.0),
    ]


# ---------------------------------------------------------------------------
# verify / veridicality
# ---------------------------------------------------------------------------

def test_verify_accepts_attested_claim():
    g = VeridicalityGuard.from_facts(facts_two_objects())
    v = g.verify({"color": "blue", "shape": "round"}, "size", "small")
    assert v.genuine and v.veridicality == 1.0
    assert bool(v) is True


def test_verify_rejects_novel_value():
    g = VeridicalityGuard.from_facts(facts_two_objects())
    v = g.verify({"color": "blue", "shape": "round"}, "size", "gigantic")
    assert not v.genuine
    assert "never stored" in v.reason


def test_verify_rejects_ghost_recombination():
    g = VeridicalityGuard.from_facts(facts_two_objects())
    # every value real, but blue+square+large never co-occurred
    v = g.verify({"color": "blue", "shape": "square"}, "size", "large")
    assert not v.genuine
    assert v.veridicality < 1.0
    assert "confabulation" in v.reason


# ---------------------------------------------------------------------------
# reconstruct + hybrid gate
# ---------------------------------------------------------------------------

def test_reconstruct_recovers_and_abstains():
    g = VeridicalityGuard.from_facts(facts_two_objects())
    assert g.reconstruct({"color": "blue", "shape": "round"}, ["size"]) == {"size": "small"}
    # unanswerable context -> abstain
    assert g.reconstruct({"color": "blue", "shape": "square"}, ["size"]) == {"size": None}


def test_guard_gates_proposed_answer():
    g = VeridicalityGuard.from_facts(facts_two_objects())
    # a retriever proposes 'small' for blue+round -> attested, passes
    assert g.guard({"color": "blue", "shape": "round"}, "size", "small") == "small"
    # a retriever proposes 'large' for blue+round -> ghost, rejected
    assert g.guard({"color": "blue", "shape": "round"}, "size", "large") is None


# ---------------------------------------------------------------------------
# verify_fact + DilmunMemory integration
# ---------------------------------------------------------------------------

def test_verify_fact_uses_entity_context():
    g = VeridicalityGuard.from_facts(facts_two_objects())
    good = Fact(entity="obj1", predicate="size", value="small", timestamp=3.0)
    bad = Fact(entity="obj1", predicate="size", value="large", timestamp=3.0)
    assert g.verify_fact(good).genuine
    assert not g.verify_fact(bad).genuine


def test_integrates_with_live_memory_without_mutating(tmp_path):
    mem = DilmunMemory(str(tmp_path / "vault"), backend="json")
    for f in facts_two_objects():
        mem.write_fact(f.entity, f.predicate, f.value)
    before = len(mem.facts())

    g = VeridicalityGuard().index(mem)
    assert g.num_entities == 2
    assert g.verify({"color": "red", "shape": "square"}, "size", "large").genuine
    assert not g.verify({"color": "red", "shape": "round"}, "size", "large").genuine

    # guard is read-only
    assert len(mem.facts()) == before


def test_deterministic_repeat():
    facts = facts_two_objects()
    g1 = VeridicalityGuard.from_facts(facts)
    g2 = VeridicalityGuard.from_facts(list(reversed(facts)))
    q = ({"color": "blue"}, "shape", "round")
    assert g1.verify(*q).veridicality == g2.verify(*q).veridicality


def test_memory_veridicality_guard_accessor(tmp_path):
    mem = DilmunMemory(str(tmp_path / "vault"), backend="json")
    for f in facts_two_objects():
        mem.write_fact(f.entity, f.predicate, f.value)
    before = len(mem.facts())

    guard = mem.veridicality_guard()
    assert guard.verify({"color": "blue", "shape": "round"}, "size", "small").genuine
    assert not guard.verify({"color": "blue", "shape": "round"}, "size", "large").genuine
    # advisory: accessor never mutates the store
    assert len(mem.facts()) == before


def test_package_level_exports():
    import dilmun
    assert dilmun.BindingMemory is BindingMemory
    assert dilmun.VeridicalityGuard is VeridicalityGuard
    assert dilmun.Verdict is Verdict
