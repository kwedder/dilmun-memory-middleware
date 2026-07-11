"""
Semantic consolidation — fold repeated episodic facts into strength-weighted
semantic facts, and reclaim the episodic instances.

DRAFT / not auto-applied. Import directly or via ``DilmunMemory.consolidate``.

Motivation (see ROBOTICS_RESEARCH.md §1)
----------------------------------------
Kim et al. (TU Delft / VU Amsterdam, arXiv:2204.01611) split an agent's memory
into an *episodic* store — specific, timestamped facts — and a *semantic* store —
generalized facts weighted by how often the regularity recurred. Repeated
episodes consolidate into one semantic fact; the instances are forgotten. Agents
with both stores generalize better as capacity grows.

Dilmun's ``(entity, predicate, value, timestamp, confidence)`` fact is already an
episodic fact. This operator adds the missing consolidation step, which matters
most on memory-tight hardware (a robot that saw "charger AtLocation dock" 20 times
should keep one strong semantic fact, not 20 episodic ones — bounded, not limited:
the same operator scales to any budget).

Design
------
Group facts by ``(generalize(entity), predicate, value)``. A group with at least
``min_support`` members becomes ONE semantic fact whose confidence accumulates the
group's evidence by the noisy-OR rule ``1 - ∏(1 - ν_i)`` — more independent
confirmations ⇒ higher confidence, saturating toward 1. Semantic facts live in the
reserved ``__semantic__`` partition.

Subsumption is conservative: a group's original facts are marked reclaimable only
when they all share the *same* entity (pure frequency consolidation). When
``generalize`` merges *different* entities into a class, the semantic fact is added
as new generalized knowledge and the specific facts are kept — generalization is
additive, never lossy about which specific thing was observed.

Everything is a pure, deterministic function of the input facts.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from .fact import Fact

SEMANTIC_EPISODE = "__semantic__"


def _noisy_or(confidences: Iterable[float]) -> float:
    """Accumulate independent evidence: 1 - ∏(1 - ν_i), clamped to [0, 1]."""
    product = 1.0
    for c in confidences:
        product *= (1.0 - c)
    return max(0.0, min(1.0, 1.0 - product))


def consolidate(
    facts: Iterable[Fact],
    *,
    generalize: Optional[Callable[[str], str]] = None,
    min_support: int = 2,
    start_seq: int = 0,
) -> Tuple[List[Fact], List[str]]:
    """Consolidate repeated episodic facts into semantic facts.

    Returns ``(semantic_facts, reclaimable_ids)``:

    * ``semantic_facts`` — one strength-weighted fact per regularity seen at
      least ``min_support`` times, in the ``__semantic__`` partition.
    * ``reclaimable_ids`` — ids of episodic facts safely subsumed by a semantic
      fact (same-entity groups only); the caller may forget these to free memory.

    Pure and deterministic: groups are processed in a stable ``repr``-sorted order.
    """
    if min_support < 1:
        raise ValueError("min_support must be >= 1")

    groups: Dict[Tuple[str, str, Any], List[Fact]] = defaultdict(list)
    for f in facts:
        entity = generalize(f.entity) if generalize is not None else f.entity
        groups[(entity, f.predicate, f.value)].append(f)

    semantic: List[Fact] = []
    reclaimable: List[str] = []
    seq = start_seq
    for (entity, predicate, value), group in sorted(groups.items(), key=lambda kv: repr(kv[0])):
        if len(group) < min_support:
            continue
        semantic.append(Fact(
            entity=entity,
            predicate=predicate,
            value=value,
            timestamp=max(g.timestamp for g in group),
            confidence=_noisy_or(g.confidence for g in group),
            episode=SEMANTIC_EPISODE,
            seq=seq,
        ))
        seq += 1
        # Only reclaim when no generalization merged distinct entities.
        if len({g.entity for g in group}) == 1:
            reclaimable.extend(g.id for g in group)
    return semantic, reclaimable
