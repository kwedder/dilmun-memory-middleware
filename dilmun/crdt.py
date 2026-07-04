"""
Distributed memory: a Last-Write-Wins Map CRDT.

MODEL.md §6 shows that Dilmun's single-store merge already obeys the
semilattice laws. Two gaps stood between that and a genuine multi-replica
CvRDT, both noted honestly in the docs:

  1. The single-store tie-break is `seq`, a per-store insertion index — not
     consistent across replicas, so two replicas could disagree on a tie.
  2. Removal (Forget) had no CRDT-safe form, so a delete on one replica could
     be "resurrected" by merging with a replica that still held the fact.

This module closes both:

  1. The winner is chosen by a **globally-consistent total order**
     `(timestamp, confidence, id)`. Every component travels with the fact —
     in particular `id` is a uuid, unique and identical on every replica — so
     all replicas pick the same winner regardless of local order.
  2. Removals are **tombstones**: a timestamped delete that participates in
     merges. A key is live iff its winning entry is a put, so a delete that
     dominates in time cannot be resurrected.

The result is a state-based CvRDT: `merge` is idempotent, commutative, and
associative (proved in MODEL.md §6), and replicas that have seen the same set
of operations converge to identical state regardless of order or batching.

This layer is opt-in and does not change single-store semantics; the default
`DilmunMemory` still uses `seq` for its local, deterministic tie-break.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple, Union

from .fact import Fact

Key = Tuple[str, str]        # (entity, predicate)


@dataclass(frozen=True)
class Tombstone:
    """A CRDT-safe deletion of a key, timestamped so it can win or lose a
    merge against a put on the same key."""
    key: Key
    timestamp: float
    id: str = field(default_factory=lambda: "rm_" + uuid.uuid4().hex[:12])
    origin: Optional[str] = None


Entry = Union[Fact, Tombstone]


def _key_of(entry: Entry) -> Key:
    if isinstance(entry, Tombstone):
        return entry.key
    return (entry.entity, entry.predicate)


def _order_of(entry: Entry) -> Tuple[float, float, str]:
    """The globally-consistent total order. A tombstone sorts as +inf in the
    confidence slot so a delete wins a same-timestamp tie (no resurrection).
    `id` is the final, globally-unique tie-break."""
    if isinstance(entry, Tombstone):
        return (entry.timestamp, float("inf"), entry.id)
    return (entry.timestamp, entry.confidence, entry.id)


class LWWMap:
    """A replicated map from `(entity, predicate)` to the winning entry.

    Immutable-in-spirit: `put`, `remove`, and `merge` return new maps, so the
    semilattice laws read cleanly and states are safe to share.
    """

    def __init__(self, entries: Optional[Dict[Key, Entry]] = None):
        self._entries: Dict[Key, Entry] = dict(entries or {})

    # -- construction --------------------------------------------------------

    @classmethod
    def from_facts(cls, facts: Iterable[Fact]) -> "LWWMap":
        m = cls()
        for f in facts:
            m = m.put(f)
        return m

    def _absorbed(self, entry: Entry) -> Dict[Key, Entry]:
        entries = dict(self._entries)
        k = _key_of(entry)
        cur = entries.get(k)
        if cur is None or _order_of(entry) > _order_of(cur):
            entries[k] = entry
        return entries

    def put(self, fact: Fact) -> "LWWMap":
        return LWWMap(self._absorbed(fact))

    def remove(self, entity: str, predicate: str, timestamp: float,
               origin: Optional[str] = None) -> "LWWMap":
        return LWWMap(self._absorbed(
            Tombstone((entity, predicate), timestamp, origin=origin)))

    # -- the CvRDT join ------------------------------------------------------

    def merge(self, other: "LWWMap") -> "LWWMap":
        """Pointwise join: per key keep the entry maximal under `_order_of`.
        Idempotent, commutative, associative (MODEL.md §6)."""
        entries = dict(self._entries)
        for k, entry in other._entries.items():
            cur = entries.get(k)
            if cur is None or _order_of(entry) > _order_of(cur):
                entries[k] = entry
        return LWWMap(entries)

    # -- observation ---------------------------------------------------------

    def live(self) -> List[Fact]:
        """The live facts: keys whose winning entry is a put, ordered by key."""
        out = [e for e in self._entries.values() if isinstance(e, Fact)]
        out.sort(key=lambda f: (f.entity, f.predicate))
        return out

    def get(self, entity: str, predicate: str) -> Optional[Fact]:
        entry = self._entries.get((entity, predicate))
        return entry if isinstance(entry, Fact) else None

    def signature(self) -> frozenset:
        """Convergence signature: the set of live (entity, predicate, value)."""
        return frozenset((f.entity, f.predicate, f.value) for f in self.live())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LWWMap):
            return NotImplemented
        return self._entries == other._entries

    def __repr__(self) -> str:
        return f"LWWMap({len(self._entries)} keys, {len(self.live())} live)"


def merge_all(maps: Iterable[LWWMap]) -> LWWMap:
    """Fold merge over many replica states. Order-independent by the
    semilattice laws."""
    result = LWWMap()
    for m in maps:
        result = result.merge(m)
    return result
