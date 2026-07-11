"""
DilmunMemory — the public interface of the memory algebra.

    from dilmun import DilmunMemory

    memory = DilmunMemory("./vault")
    memory.open_episode("chat_001")
    memory.write_fact(entity="user", predicate="favorite_color",
                      value="blue", confidence=0.95)
    context = memory.get_context()
    memory.close_episode()

The memory state M is partitioned into a global component M_0 and episode
components M_1 ... M_k. Facts written inside an open episode land in that
episode; facts written outside any episode land in M_0. Retrieval sees
M_0 ∪ M_active, so episodes are isolated by default and promotion across
episodes is explicit (promote()).
"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from .backends import Backend, make_backend
from .fact import Fact
from .normalization import PredicateRegistry, default_normalize, normalize
from .operators import (
    DEFAULT_WEIGHTS,
    build_graph,
    canonicalize,
    compose,
    composable,
    derive,
    forget,
    merge,
    retrieve,
)


class DilmunMemory:
    """Persistent, deterministic memory for long-horizon agents."""

    def __init__(
        self,
        vault_path: str = "./vault",
        backend: str = "json",
        *,
        min_confidence: float = 0.0,
        weights: Tuple[float, float, float] = DEFAULT_WEIGHTS,
        predicates: Optional[PredicateRegistry] = None,
    ):
        self.backend: Backend = make_backend(backend, vault_path)
        self.min_confidence = min_confidence
        self.weights = weights
        self.predicates = predicates
        self._facts: List[Fact] = self.backend.load()
        self._episodes: Dict[str, Dict] = self.backend.load_episodes()
        self._seq = 1 + max((f.seq for f in self._facts), default=-1)
        self._active_episode: Optional[str] = None

    # ------------------------------------------------------------------
    # episodes — graded partitioning M = M_0 ∪ M_1 ∪ ... ∪ M_k
    # ------------------------------------------------------------------

    def open_episode(self, episode_id: str, tags: Optional[List[str]] = None) -> None:
        """Open (or re-open) an episode; subsequent writes land in it."""
        record = self._episodes.setdefault(
            episode_id, {"opened_at": time.time(), "tags": tags or []}
        )
        record.pop("closed_at", None)
        self._active_episode = episode_id
        self.backend.save_episodes(self._episodes)

    def close_episode(self) -> None:
        """Close the active episode; writes fall back to global M_0."""
        if self._active_episode:
            self._episodes[self._active_episode]["closed_at"] = time.time()
            self.backend.save_episodes(self._episodes)
        self._active_episode = None

    @property
    def active_episode(self) -> Optional[str]:
        return self._active_episode

    def episodes(self) -> Dict[str, Dict]:
        return dict(self._episodes)

    # ------------------------------------------------------------------
    # writing — immutable, append-only
    # ------------------------------------------------------------------

    def write_fact(
        self,
        entity: str,
        predicate: str,
        value: Any,
        confidence: float = 1.0,
        *,
        episode: Optional[str] = None,
        ttl: Optional[float] = None,
        timestamp: Optional[float] = None,
    ) -> Fact:
        """Append a new immutable fact (e, p, v, t, ν).

        ttl — seconds until the fact enters the forgetting operator's
        domain; omit for facts that never expire.
        """
        now = time.time()
        if self.predicates is not None:
            predicate = self.predicates.normalize(predicate)
        else:
            predicate = default_normalize(predicate)
        fact = Fact(
            entity=entity,
            predicate=predicate,
            value=value,
            timestamp=now if timestamp is None else timestamp,
            confidence=confidence,
            episode=episode or self._active_episode,
            seq=self._seq,
            expires_at=None if ttl is None else now + ttl,
        )
        self._seq += 1
        self._facts.append(fact)
        self.backend.append(fact)
        return fact

    def promote(self, fact: Union[Fact, str]) -> Fact:
        """Explicit cross-episode promotion: copy a fact into global M_0.

        The original episode fact is untouched (facts are immutable);
        the promotion is a new fact in M_0.
        """
        source = self._resolve(fact)
        if source.episode is None:
            return source
        promoted = Fact(
            entity=source.entity,
            predicate=source.predicate,
            value=source.value,
            timestamp=source.timestamp,
            confidence=source.confidence,
            episode=None,
            seq=self._seq,
            expires_at=source.expires_at,
            derived_from=None,
        )
        self._seq += 1
        self._facts.append(promoted)
        self.backend.append(promoted)
        return promoted

    # ------------------------------------------------------------------
    # reading — structured retrieval
    # ------------------------------------------------------------------

    def facts(self, episode: Optional[str] = "__visible__") -> List[Fact]:
        """Raw facts. Default view is M_0 ∪ M_active; pass an episode id
        for that partition only, or None for the global partition M_0."""
        if episode == "__visible__":
            visible = {None, self._active_episode}
            return [f for f in self._facts if f.episode in visible]
        return [f for f in self._facts if f.episode == episode]

    def get_context(
        self,
        limit: Optional[int] = None,
        *,
        weights: Optional[Tuple[float, float, float]] = None,
        now: Optional[float] = None,
    ) -> List[Fact]:
        """The retrieval function.

        Pipeline over the visible state M_0 ∪ M_active:

            1. F — drop expired / low-confidence facts (read-time view;
                   the store is not modified)
            2. C — canonicalize conflicts
            3. score(f) = w1·ν(f) + w2·recency + w3·graph_centrality,
               returned best-first
        """
        live = forget(
            self.facts(), now=now, min_confidence=self.min_confidence
        )
        canonical = canonicalize(live)
        return retrieve(
            canonical, limit=limit, weights=weights or self.weights, now=now
        )

    def query(
        self,
        entity: Optional[str] = None,
        predicate: Optional[str] = None,
        value: Any = None,
    ) -> List[Fact]:
        """Canonical facts from the visible state, filtered by any of
        entity / predicate / value."""
        results = canonicalize(forget(self.facts(), min_confidence=self.min_confidence))
        if entity is not None:
            results = [f for f in results if f.entity == entity]
        if predicate is not None:
            results = [f for f in results if f.predicate == predicate]
        if value is not None:
            results = [f for f in results if f.value == value]
        return results

    # ------------------------------------------------------------------
    # veridicality — advisory confabulation guard (read-only)
    # ------------------------------------------------------------------

    def veridicality_guard(self, *, threshold: float = 1.0) -> "VeridicalityGuard":
        """Build a confabulation guard over the current visible state.

        Advisory only: the guard is a read-side verification layer that can tell
        a genuine stored memory from a synthesized one (a value never seen, or a
        combination of seen values that never co-occurred). It never mutates the
        store and never blocks a write — callers decide what to do with a
        Verdict. Rebuilt from the current facts on each call.

            guard = memory.veridicality_guard()
            guard.verify_fact(incoming_fact)              # write-path check
            guard.guard({"color": "blue"}, "size", "small")   # gate a proposal
        """
        from .guard import VeridicalityGuard
        return VeridicalityGuard(threshold=threshold).index_facts(self.facts())

    # ------------------------------------------------------------------
    # graph structure
    # ------------------------------------------------------------------

    def graph(self) -> Dict[str, List[Tuple[str, Any]]]:
        """Adjacency of the canonical visible state:
        entity -> [(predicate, value), ...]."""
        return build_graph(canonicalize(self.facts()))

    def neighbors(self, entity: str) -> List[Tuple[str, Any]]:
        """Outgoing edges of an entity in the memory graph."""
        return self.graph().get(entity, [])

    # ------------------------------------------------------------------
    # operators applied to the store
    # ------------------------------------------------------------------

    def canonicalize(self, *, apply: bool = False) -> List[Fact]:
        """C over the visible state. With apply=True, conflicting
        non-canonical facts are compacted out of the store (per
        partition, so episodes never cannibalize each other)."""
        if not apply:
            return canonicalize(self.facts())
        partitions: Dict[Optional[str], List[Fact]] = {}
        for f in self._facts:
            partitions.setdefault(f.episode, []).append(f)
        kept: List[Fact] = []
        for partition in partitions.values():
            kept.extend(canonicalize(partition))
        kept.sort(key=lambda f: f.seq)
        self._facts = kept
        self.backend.replace_all(kept)
        return canonicalize(self.facts())

    def normalize(self, *, apply: bool = False) -> List[Fact]:
        """Normalize predicates over the whole store using the configured
        registry (or default normalization if none). With apply=True the
        store is rewritten with normalized predicates, which lets
        previously-fragmented aliases collapse under canonicalize()."""
        normalized = normalize(self._facts, self.predicates)
        if apply:
            self._facts = normalized
            self.backend.replace_all(normalized)
        return normalized

    def merge(
        self,
        other: Union["DilmunMemory", Iterable[Fact]],
    ) -> List[Fact]:
        """merge(self, other) = C(self ∪ other) over the global-visible
        states. Read-only: returns the canonical merged facts without
        mutating either store. Commutative and associative."""
        other_facts = other.facts() if isinstance(other, DilmunMemory) else list(other)
        return merge(self.facts(), other_facts)

    def forget(
        self,
        *,
        now: Optional[float] = None,
        min_confidence: Optional[float] = None,
        contradiction_pressure: bool = False,
    ) -> int:
        """F applied to the whole store (all partitions). Returns the
        number of facts removed. Idempotent: a second call with the
        same arguments removes nothing."""
        threshold = self.min_confidence if min_confidence is None else min_confidence
        partitions: Dict[Optional[str], List[Fact]] = {}
        for f in self._facts:
            partitions.setdefault(f.episode, []).append(f)
        kept: List[Fact] = []
        for partition in partitions.values():
            kept.extend(forget(
                partition,
                now=now,
                min_confidence=threshold,
                contradiction_pressure=contradiction_pressure,
            ))
        kept.sort(key=lambda f: f.seq)
        removed = len(self._facts) - len(kept)
        if removed:
            self._facts = kept
            self.backend.replace_all(kept)
        return removed

    def compose(self, f1: Union[Fact, str], f2: Union[Fact, str], *, write: bool = False) -> Fact:
        """comp(f1, f2) — valid when f1.value == f2.entity. With
        write=True the derived fact is persisted."""
        derived_fact = compose(self._resolve(f1), self._resolve(f2), seq=self._seq)
        if write:
            self._seq += 1
            self._facts.append(derived_fact)
            self.backend.append(derived_fact)
        return derived_fact

    def derive(self, *, write: bool = False) -> List[Fact]:
        """One step of path composition over the canonical visible
        state. With write=True derived facts are persisted."""
        derived_facts = derive(canonicalize(self.facts()), start_seq=self._seq)
        if write:
            for fact in derived_facts:
                self._seq = fact.seq + 1
                self._facts.append(fact)
                self.backend.append(fact)
        return derived_facts

    # ------------------------------------------------------------------
    # plumbing
    # ------------------------------------------------------------------

    def _resolve(self, fact: Union[Fact, str]) -> Fact:
        if isinstance(fact, Fact):
            return fact
        for f in self._facts:
            if f.id == fact:
                return f
        raise KeyError(f"no fact with id {fact!r}")

    def close(self) -> None:
        self.backend.close()

    def __enter__(self) -> "DilmunMemory":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
