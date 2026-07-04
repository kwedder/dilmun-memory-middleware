"""
Deterministic operators over memory states.

A memory state is a finite set of facts M = {f_1, ..., f_n}. Every operator
here is a pure function M -> M (or M -> derived structure) with the formal
properties promised in the README:

    canonicalize (C) — idempotent, deterministic conflict resolution
    forget       (F) — idempotent closure operator over stale facts
    compose          — relational (path) composition over the memory graph
    retrieve         — structured scoring, not probabilistic guessing
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .fact import Fact

# score(f) = w1·ν(f) + w2·recency + w3·graph_centrality
DEFAULT_WEIGHTS: Tuple[float, float, float] = (0.5, 0.3, 0.2)


# ---------------------------------------------------------------------------
# C — canonicalization
# ---------------------------------------------------------------------------

def canonicalize(facts: Iterable[Fact]) -> List[Fact]:
    """C : M -> M — deterministic conflict resolution.

    Facts sharing (entity, predicate) collapse to a single canonical
    representative, selected by:

        1. highest timestamp
        2. highest confidence
        3. stable insertion order (lowest seq wins the tie)

    Properties: C(C(M)) = C(M) and M1 = M2 => C(M1) = C(M2).
    The result is ordered by insertion order (seq), so equal inputs
    always yield identical outputs.
    """
    groups: Dict[Tuple[str, str], List[Fact]] = defaultdict(list)
    for fact in facts:
        groups[fact.key].append(fact)

    canonical = [
        min(group, key=lambda f: (-f.timestamp, -f.confidence, f.seq))
        for group in groups.values()
    ]
    canonical.sort(key=lambda f: f.seq)
    return canonical


# ---------------------------------------------------------------------------
# F — forgetting
# ---------------------------------------------------------------------------

def forget(
    facts: Iterable[Fact],
    *,
    now: Optional[float] = None,
    min_confidence: float = 0.0,
    contradiction_pressure: bool = False,
) -> List[Fact]:
    """F : M -> M — closure-style forgetting, not deletion.

    A fact is removed when it satisfies any of:

        * expired timestamp   (fact.expires_at <= now)
        * low confidence      (fact.confidence < min_confidence)
        * contradiction pressure (optional policy: it lost canonicalization
          to a fact with a different value)

    F is idempotent for a fixed `now`: F(F(M)) = F(M).
    """
    now = time.time() if now is None else now
    kept = [
        f for f in facts
        if not f.is_expired(now) and f.confidence >= min_confidence
    ]

    if contradiction_pressure:
        winners = {f.key: f for f in canonicalize(kept)}
        kept = [
            f for f in kept
            if f.id == winners[f.key].id or f.value == winners[f.key].value
        ]

    kept.sort(key=lambda f: f.seq)
    return kept


# ---------------------------------------------------------------------------
# comp — relational composition (path composition over the memory graph)
# ---------------------------------------------------------------------------

def composable(f1: Fact, f2: Fact) -> bool:
    """Composition comp(f1, f2) is valid when f1.v = f2.e."""
    return f1.value == f2.entity


def compose(f1: Fact, f2: Fact, *, seq: int = 0) -> Fact:
    """comp(f1, f2) — derive a new fact by path composition.

        (A, likes, B) ∘ (B, category, C)  =>  (A, likes_category, C)

    The derived fact carries confidence ν(f1)·ν(f2), the newer of the two
    timestamps, and provenance back to both parents. Cross-episode
    compositions land in the global partition M_0.
    """
    if not composable(f1, f2):
        raise ValueError(
            f"comp(f1, f2) requires f1.value == f2.entity, "
            f"got {f1.value!r} vs {f2.entity!r}"
        )
    return Fact(
        entity=f1.entity,
        predicate=f"{f1.predicate}_{f2.predicate}",
        value=f2.value,
        timestamp=max(f1.timestamp, f2.timestamp),
        confidence=f1.confidence * f2.confidence,
        episode=f1.episode if f1.episode == f2.episode else None,
        seq=seq,
        derived_from=(f1.id, f2.id),
    )


def derive(facts: Sequence[Fact], *, start_seq: int = 0) -> List[Fact]:
    """All valid pairwise compositions over a set of facts.

    This is one step of path-based derivation over the memory graph;
    apply repeatedly for longer paths.
    """
    derived: List[Fact] = []
    seq = start_seq
    ordered = sorted(facts, key=lambda f: f.seq)
    for f1 in ordered:
        for f2 in ordered:
            if f1.id != f2.id and composable(f1, f2):
                derived.append(compose(f1, f2, seq=seq))
                seq += 1
    return derived


# ---------------------------------------------------------------------------
# memory graph
# ---------------------------------------------------------------------------

def build_graph(facts: Iterable[Fact]) -> Dict[str, List[Tuple[str, Any]]]:
    """Facts induce a directed labeled graph.

        nodes  = entities (and the values they point at)
        edges  = predicates

    Returns adjacency: entity -> [(predicate, value), ...] in seq order.
    """
    adjacency: Dict[str, List[Tuple[str, Any]]] = defaultdict(list)
    for fact in sorted(facts, key=lambda f: f.seq):
        adjacency[fact.entity].append((fact.predicate, fact.value))
    return dict(adjacency)


def degree_centrality(facts: Iterable[Fact]) -> Dict[str, float]:
    """Degree centrality per node, normalized to [0, 1].

    Both endpoints of every edge count: entities gain out-degree,
    values gain in-degree.
    """
    degree: Dict[str, int] = defaultdict(int)
    for fact in facts:
        degree[str(fact.entity)] += 1
        degree[str(fact.value)] += 1
    if not degree:
        return {}
    max_degree = max(degree.values())
    return {node: d / max_degree for node, d in degree.items()}


# ---------------------------------------------------------------------------
# retrieval — structured scoring
# ---------------------------------------------------------------------------

def score_facts(
    facts: Sequence[Fact],
    *,
    weights: Tuple[float, float, float] = DEFAULT_WEIGHTS,
    now: Optional[float] = None,
) -> Dict[str, float]:
    """score(f) = w1·ν(f) + w2·recency + w3·graph_centrality

    recency is normalized over the timestamps present in the set
    (newest = 1, oldest = 0; a single-timestamp set scores 1).
    Returns {fact.id: score}.
    """
    if not facts:
        return {}
    w1, w2, w3 = weights
    timestamps = [f.timestamp for f in facts]
    t_min, t_max = min(timestamps), max(timestamps)
    span = t_max - t_min
    centrality = degree_centrality(facts)

    scores: Dict[str, float] = {}
    for f in facts:
        recency = 1.0 if span == 0 else (f.timestamp - t_min) / span
        scores[f.id] = (
            w1 * f.confidence
            + w2 * recency
            + w3 * centrality.get(str(f.entity), 0.0)
        )
    return scores


def retrieve(
    facts: Sequence[Fact],
    *,
    limit: Optional[int] = None,
    weights: Tuple[float, float, float] = DEFAULT_WEIGHTS,
    now: Optional[float] = None,
) -> List[Fact]:
    """Return facts ordered by descending score (argmax_M score(f)).

    Ties break on newer timestamp, then insertion order, so retrieval
    is fully deterministic.
    """
    scores = score_facts(facts, weights=weights, now=now)
    ranked = sorted(
        facts, key=lambda f: (-scores[f.id], -f.timestamp, f.seq)
    )
    return ranked if limit is None else ranked[:limit]
