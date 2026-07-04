"""
Fact — the atomic unit of Dilmun memory.

A fact is the 5-tuple described in the README:

    f = (e, p, v, t, ν)

    e — entity
    p — predicate
    v — value
    t — timestamp (seconds since epoch)
    ν — confidence valuation in [0, 1]

Facts are immutable: an update never mutates an existing fact, it appends a
new one. Conflicts between facts sharing (entity, predicate) are resolved by
the canonicalization operator C (see operators.canonicalize).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass(frozen=True)
class Fact:
    """An immutable fact (e, p, v, t, ν) plus bookkeeping fields.

    episode      — id of the episode partition M_i the fact belongs to;
                   None means the global partition M_0.
    seq          — stable insertion order; final tie-breaker in C.
    expires_at   — absolute expiry (epoch seconds) used by the forgetting
                   operator F; None means the fact never expires.
    derived_from — (id_1, id_2) when the fact was produced by relational
                   composition comp(f1, f2); None for written facts.
    """

    entity: str
    predicate: str
    value: Any
    timestamp: float
    confidence: float = 1.0
    episode: Optional[str] = None
    seq: int = 0
    id: str = field(default_factory=_new_id)
    expires_at: Optional[float] = None
    derived_from: Optional[Tuple[str, str]] = None

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be a valuation in [0, 1], got {self.confidence}"
            )

    @property
    def key(self) -> Tuple[str, str]:
        """Conflict key: facts conflict when they share (entity, predicate)
        but carry different values."""
        return (self.entity, self.predicate)

    def is_expired(self, now: Optional[float] = None) -> bool:
        if self.expires_at is None:
            return False
        return (time.time() if now is None else now) >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity": self.entity,
            "predicate": self.predicate,
            "value": self.value,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "episode": self.episode,
            "seq": self.seq,
            "expires_at": self.expires_at,
            "derived_from": list(self.derived_from) if self.derived_from else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Fact":
        derived = data.get("derived_from")
        return cls(
            entity=data["entity"],
            predicate=data["predicate"],
            value=data["value"],
            timestamp=float(data["timestamp"]),
            confidence=float(data.get("confidence", 1.0)),
            episode=data.get("episode"),
            seq=int(data.get("seq", 0)),
            id=data.get("id") or _new_id(),
            expires_at=data.get("expires_at"),
            derived_from=tuple(derived) if derived else None,
        )
