"""
VeridicalityGuard — a confabulation gate over a DilmunMemory.

DRAFT / not wired into the package (`dilmun/__init__.py` untouched).
Import directly:  ``from dilmun.guard import VeridicalityGuard``.

Why this shape
--------------
A final benchmark against an embedding/RAG-style store (see `BUILD_REPORT.md`
§3b) found that the strongest configuration is not to *replace* similarity
retrieval but to *guard* it: let any retriever propose an answer, then gate it
through a relational veridicality check. The hybrid matched the leader's recall
(0.976), abstained most reliably on unanswerable queries (0.984), and had the
lowest confident-error rate (0.020) — with no threshold to tune.

This guard is that gate. It reads the canonical facts of a `DilmunMemory`, treats
each entity's ``(predicate, value)`` bundle as a co-observed record, and binds
them into a `BindingMemory`. It then answers, deterministically and without any
learned parameters:

    verify(known, predicate, value) -> Verdict   # is this claim genuine?
    reconstruct(known, targets)     -> {pred: value|None}   # fill, or abstain
    guard(known, predicate, value)  -> value | None          # the hybrid gate

It never mutates the memory; it is a read-side verification layer.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .binding import BindingMemory, Node
from .fact import Fact
from .operators import canonicalize


@dataclass(frozen=True)
class Verdict:
    """Outcome of a veridicality check.

    genuine       — whether the claim clears the threshold
    veridicality  — graded relational support in [0, 1]
    reason        — short human-readable explanation of the verdict
    """

    genuine: bool
    veridicality: float
    reason: str

    def __bool__(self) -> bool:
        return self.genuine


class VeridicalityGuard:
    """Read-side confabulation gate built from a memory's co-occurrence graph."""

    def __init__(self, *, threshold: float = 1.0) -> None:
        self.threshold = threshold
        self._bm = BindingMemory()
        self._entity_cells: Dict[str, List[Node]] = {}

    # -- construction -------------------------------------------------------

    @classmethod
    def from_facts(cls, facts: Iterable[Fact], *, threshold: float = 1.0) -> "VeridicalityGuard":
        g = cls(threshold=threshold)
        g.index_facts(facts)
        return g

    def index(self, memory) -> "VeridicalityGuard":
        """Build the guard from a DilmunMemory's visible state."""
        return self.index_facts(memory.facts())

    def index_facts(self, facts: Iterable[Fact]) -> "VeridicalityGuard":
        """Canonicalize, then bind each entity's ``(predicate, value)`` bundle
        as one co-observed record."""
        canonical = canonicalize(facts)
        by_entity: Dict[str, List[Fact]] = defaultdict(list)
        for f in canonical:
            by_entity[f.entity].append(f)
        for entity, group in sorted(by_entity.items(), key=lambda kv: repr(kv[0])):
            cells: List[Node] = [(f.predicate, f.value) for f in group]
            self._entity_cells[entity] = cells
            self._bm.store_record(cells)
        return self

    # -- core checks --------------------------------------------------------

    def veridicality(self, cells: Iterable[Node]) -> float:
        return self._bm.veridicality(cells)

    def verify(
        self,
        known: Dict[str, Any],
        predicate: str,
        value: Any,
        *,
        threshold: Optional[float] = None,
    ) -> Verdict:
        """Is asserting ``predicate = value`` alongside the ``known`` cells a
        genuine, attested combination? Rejects both novel values and novel
        combinations of seen values (ghost memories)."""
        thr = self.threshold if threshold is None else threshold
        claim: Node = (predicate, value)
        if not self._bm.knows_value(predicate, value):
            return Verdict(False, 0.0, f"value {value!r} never stored for {predicate!r}")
        cells = [(p, v) for p, v in known.items()] + [claim]
        vd = self._bm.veridicality(cells)
        if vd >= thr:
            return Verdict(True, vd, "attested: forms a stored clique with the context")
        return Verdict(False, vd, "unattested combination (possible confabulation)")

    def verify_fact(self, fact: Fact, *, threshold: Optional[float] = None) -> Verdict:
        """Verify a fact against what is already known about its entity.

        Natural write-path hook: before trusting a recalled/asserted fact, check
        it is consistent with the entity's established co-occurrence structure.
        A brand-new entity (no context) is accepted iff the value has been seen
        for that predicate at all.
        """
        context = {
            p: v for (p, v) in self._entity_cells.get(fact.entity, [])
            if p != fact.predicate
        }
        return self.verify(context, fact.predicate, fact.value, threshold=threshold)

    def is_genuine(self, cells: Iterable[Node], *, threshold: Optional[float] = None) -> bool:
        thr = self.threshold if threshold is None else threshold
        return self._bm.veridicality(list(cells)) >= thr

    # -- reconstruction + the hybrid gate ----------------------------------

    def reconstruct(
        self,
        known: Dict[str, Any],
        targets: Sequence[str],
        *,
        threshold: Optional[float] = None,
    ) -> Dict[str, Optional[Any]]:
        """Fill missing predicates from the known cells, abstaining (None) rather
        than confabulate. Delegates to the binding memory's clique decoding."""
        thr = self.threshold if threshold is None else threshold
        return self._bm.reconstruct(known, targets, min_binding=thr)

    def guard(
        self,
        known: Dict[str, Any],
        predicate: str,
        candidate: Any,
        *,
        threshold: Optional[float] = None,
    ) -> Optional[Any]:
        """The hybrid gate: return ``candidate`` (e.g. proposed by a vector/RAG
        retriever) only if it is an attested combination, else ``None``. This is
        the configuration that beat the tuned leader in the benchmark."""
        return candidate if self.verify(known, predicate, candidate, threshold=threshold).genuine else None

    # -- introspection ------------------------------------------------------

    @property
    def num_entities(self) -> int:
        return len(self._entity_cells)

    def __repr__(self) -> str:
        return f"VeridicalityGuard(entities={self.num_entities}, threshold={self.threshold}, {self._bm!r})"
