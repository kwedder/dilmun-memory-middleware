"""Tests for semantic consolidation (dilmun/consolidate.py).

    * repeated same-entity observations fold into one stronger semantic fact
    * confidence accumulates by noisy-OR (more confirmations -> higher)
    * min_support gates what consolidates
    * cross-entity generalization adds knowledge WITHOUT reclaiming specifics
    * DilmunMemory.consolidate is advisory by default; apply=True shrinks store
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from dilmun import DilmunMemory, Fact, consolidate, SEMANTIC_EPISODE


def obs(entity, predicate, value, t, conf=1.0, seq=0):
    return Fact(entity=entity, predicate=predicate, value=value,
               timestamp=t, confidence=conf, seq=seq)


# ---------------------------------------------------------------------------
# pure operator
# ---------------------------------------------------------------------------

def test_repeated_observations_fold_into_one_semantic_fact():
    facts = [
        obs("charger", "at", "dock", 1.0, seq=0),
        obs("charger", "at", "dock", 2.0, seq=1),
        obs("charger", "at", "dock", 3.0, seq=2),
    ]
    semantic, reclaimable = consolidate(facts, min_support=2)
    assert len(semantic) == 1
    s = semantic[0]
    assert (s.entity, s.predicate, s.value) == ("charger", "at", "dock")
    assert s.episode == SEMANTIC_EPISODE
    assert s.timestamp == 3.0                       # newest observation
    assert len(reclaimable) == 3                    # all three instances reclaimable


def test_confidence_accumulates_by_noisy_or():
    facts = [obs("x", "p", "v", 1.0, conf=0.5, seq=0),
             obs("x", "p", "v", 2.0, conf=0.5, seq=1)]
    semantic, _ = consolidate(facts, min_support=2)
    # 1 - (1-0.5)(1-0.5) = 0.75
    assert abs(semantic[0].confidence - 0.75) < 1e-9


def test_min_support_gates_consolidation():
    facts = [obs("x", "p", "v", 1.0), obs("y", "q", "w", 1.0)]
    semantic, reclaimable = consolidate(facts, min_support=2)
    assert semantic == [] and reclaimable == []


def test_generalization_adds_without_reclaiming_specifics():
    # two different robots seen charging -> generalize to a class
    facts = [
        obs("robotA", "state", "charging", 1.0, seq=0),
        obs("robotB", "state", "charging", 2.0, seq=1),
    ]
    semantic, reclaimable = consolidate(
        facts, generalize=lambda e: "robot", min_support=2
    )
    assert len(semantic) == 1
    assert semantic[0].entity == "robot"
    # cross-entity: specifics are NOT reclaimed (generalization is additive)
    assert reclaimable == []


def test_deterministic_order_independent():
    facts = [obs("a", "p", str(i % 2), float(i), seq=i) for i in range(6)]
    s1, r1 = consolidate(facts, min_support=2)
    s2, r2 = consolidate(list(reversed(facts)), min_support=2)
    key = lambda fs: sorted((f.entity, f.predicate, f.value, round(f.confidence, 6)) for f in fs)
    assert key(s1) == key(s2)
    assert sorted(r1) == sorted(r2)


# ---------------------------------------------------------------------------
# DilmunMemory integration
# ---------------------------------------------------------------------------

def test_memory_consolidate_advisory_then_apply(tmp_path):
    mem = DilmunMemory(str(tmp_path / "vault"), backend="json")
    for t in range(3):
        mem.write_fact("charger", "at", "dock", timestamp=float(t))
    before = len(mem.facts())

    # advisory: previews without mutating
    preview = mem.consolidate(min_support=2)
    assert len(preview) == 1
    assert len(mem.facts()) == before

    # apply: adds the semantic fact, reclaims the 3 episodic instances -> net shrink
    mem.consolidate(min_support=2, apply=True)
    after = mem.facts()
    assert len(after) < before
    semantic = [f for f in after if f.episode == SEMANTIC_EPISODE]
    assert len(semantic) == 1 and semantic[0].value == "dock"
