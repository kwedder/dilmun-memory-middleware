"""
Hybrid Logical Clock (HLC) — causal timestamps that stay close to physical time.

Why this exists
---------------
Dilmun's distributed merge (``crdt.LWWMap``) picks the winning fact by
``(timestamp, confidence, id)``. If ``timestamp`` is a raw wall clock, drifting
robot clocks corrupt the winner: a swarm stress test measured wall-clock LWW
choosing the WRONG (not causally-latest) value 24-73% of the time under realistic
skew, while a logical clock was correct 100% of the time.

An HLC (Kulkarni et al., 2014) is the fix that fits Dilmun specifically. Unlike a
plain Lamport counter it keeps a *physical* component, so the timestamp still
means roughly "when" — which Dilmun relies on for recency scoring, TTL, and
``forget``. And unlike vector clocks its size is O(1), which matters on an ESP32.

Representation
--------------
An HLC timestamp is a pair ``(l, c)``:
  * ``l`` — the largest physical time (ms) this node has seen (its own or a peer's)
  * ``c`` — a logical counter that breaks ties when events share the same ``l``

``pack()`` folds the pair into a single Python int that sorts by ``(l, c)`` and is
drop-in usable as ``Fact.timestamp`` on the gossip path — no change to LWWMap.
Use HLC timestamps *consistently* on the distributed path (don't mix with raw
wall-clock floats in the same replicated store).

Limitation & upgrade path
--------------------------
An HLC gives a total order, so it *resolves* every conflict but cannot *detect*
concurrency (two writes with no causal link). If you later need to flag genuine
concurrent conflicts to the veridicality guard instead of silently resolving them,
that is where an Interval Tree Clock / version-vector layer plugs in — see
``concurrent()`` below, which is the documented hook.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from .fact import Fact

_C_BITS = 32                      # counter occupies the low 32 bits of a packed ts


def _now_ms(now: Optional[float]) -> int:
    """Physical time in integer milliseconds (injectable for determinism)."""
    return int((time.time() if now is None else now) * 1000)


@dataclass(frozen=True, order=True)
class HLCTimestamp:
    """An immutable HLC reading ``(l, c)``. Ordered lexicographically by design."""
    l: int      # physical component (ms)
    c: int      # logical counter

    def pack(self) -> int:
        """A single int that sorts identically to ``(l, c)`` — use as Fact.timestamp."""
        return (self.l << _C_BITS) | self.c

    @classmethod
    def unpack(cls, packed: int) -> "HLCTimestamp":
        packed = int(packed)
        return cls(packed >> _C_BITS, packed & ((1 << _C_BITS) - 1))


class HLC:
    """A per-node hybrid logical clock. One instance per robot."""

    def __init__(self, node_id: str = "", *, l: int = 0, c: int = 0) -> None:
        self.node_id = node_id
        self.l = l
        self.c = c

    def _reading(self) -> HLCTimestamp:
        return HLCTimestamp(self.l, self.c)

    def local(self, now: Optional[float] = None) -> HLCTimestamp:
        """Stamp a local event. Advances past physical time, else bumps the counter."""
        pt = _now_ms(now)
        l_prev = self.l
        self.l = max(l_prev, pt)
        self.c = self.c + 1 if self.l == l_prev else 0
        return self._reading()

    def receive(self, remote: HLCTimestamp, now: Optional[float] = None) -> HLCTimestamp:
        """Update the clock on receiving a peer's timestamp (call when merging a
        remote fact). Guarantees the next local stamp is strictly after ``remote``."""
        pt = _now_ms(now)
        l_prev, c_prev = self.l, self.c
        l_new = max(l_prev, remote.l, pt)
        if l_new == l_prev and l_new == remote.l:
            c_new = max(c_prev, remote.c) + 1
        elif l_new == l_prev:
            c_new = c_prev + 1
        elif l_new == remote.l:
            c_new = remote.c + 1
        else:
            c_new = 0
        self.l, self.c = l_new, c_new
        return self._reading()


# ---------------------------------------------------------------------------
# Fact integration for the gossip path
# ---------------------------------------------------------------------------

def stamp_fact(
    clock: HLC,
    entity: str,
    predicate: str,
    value,
    *,
    confidence: float = 1.0,
    episode: Optional[str] = None,
    seq: int = 0,
    now: Optional[float] = None,
) -> Fact:
    """Create a Fact whose ``timestamp`` is an HLC-packed causal timestamp."""
    ts = clock.local(now).pack()
    return Fact(
        entity=entity, predicate=predicate, value=value,
        timestamp=ts, confidence=confidence, episode=episode, seq=seq,
    )


def observe_fact(clock: HLC, fact: Fact, now: Optional[float] = None) -> HLCTimestamp:
    """Advance the local clock past an incoming HLC-stamped fact. Call this when
    merging a remote fact so the node's clock never falls behind a peer."""
    return clock.receive(HLCTimestamp.unpack(int(fact.timestamp)), now)


# ---------------------------------------------------------------------------
# Concurrency (the documented ITC upgrade hook)
# ---------------------------------------------------------------------------

def happens_before(a: HLCTimestamp, b: HLCTimestamp) -> bool:
    """True if ``a`` causally precedes ``b`` under the HLC total order."""
    return a < b


def concurrent(a: HLCTimestamp, b: HLCTimestamp) -> bool:
    """HLC imposes a total order, so nothing is ever *detected* as concurrent
    (equal readings excepted). This always-False result is intentional and is the
    seam where an Interval Tree Clock / version vector would later return True for
    genuinely concurrent writes, letting the guard flag a conflict instead of
    silently resolving it. Kept explicit so that upgrade is a drop-in."""
    return False
