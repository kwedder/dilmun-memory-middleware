"""
Predicate normalization.

Without normalization, these are four different facts:

    (A, owns, B)
    (A, possesses, B)
    (A, has, B)
    (A, is_owner_of, B)

so canonicalization never fires and the algebra fragments. A
PredicateRegistry maps a family of surface aliases onto one canonical
predicate, so the four collapse to a single fact:

    (A, OWNS, B)

Normalization is what makes the rest of the algebra stable: once
predicates are canonical, conflicting values share a key and C can
resolve them.

Two layers:

  * default normalization — casefold, strip, collapse internal
    whitespace/hyphens to single underscores. Applied to every
    predicate, registry or not. So "is owner of" -> "is_owner_of".
  * registry normalization — an explicit alias -> canonical map, applied
    on top of the default form. So {"OWNS": ["owns", "possesses", "has"]}
    sends all three to "OWNS".
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional

from .fact import Fact

_WS = re.compile(r"[\s\-]+")


def default_normalize(predicate: str) -> str:
    """Casefold, strip, and collapse whitespace/hyphens to underscores.

    This is a total, deterministic function applied to every predicate
    even when no registry is configured.
    """
    return _WS.sub("_", predicate.strip().casefold()).strip("_")


class PredicateRegistry:
    """An explicit alias -> canonical predicate map.

    >>> reg = PredicateRegistry()
    >>> reg.register("OWNS", "owns", "possesses", "has", "is owner of")
    >>> reg.normalize("possesses")
    'OWNS'
    >>> reg.normalize("likes")        # unknown: default form, passed through
    'likes'
    """

    def __init__(self) -> None:
        # maps default-normalized alias -> canonical predicate
        self._aliases: Dict[str, str] = {}

    def register(self, canonical: str, *aliases: str) -> "PredicateRegistry":
        """Map every alias (and the canonical itself) onto `canonical`."""
        for surface in (canonical, *aliases):
            self._aliases[default_normalize(surface)] = canonical
        return self

    def normalize(self, predicate: str) -> str:
        """Canonical predicate for a surface form.

        Registry hit wins; otherwise the default-normalized form is
        returned unchanged (an unknown predicate is still stabilized,
        just not merged with a family).
        """
        key = default_normalize(predicate)
        return self._aliases.get(key, key)

    def canonical_predicates(self) -> List[str]:
        return sorted(set(self._aliases.values()))

    def __contains__(self, predicate: str) -> bool:
        return default_normalize(predicate) in self._aliases


def normalize(
    facts: Iterable[Fact],
    registry: Optional[PredicateRegistry] = None,
) -> List[Fact]:
    """Normalize the predicates of a set of facts.

    Returns new Fact objects (facts are immutable) that preserve id,
    timestamp, confidence, episode, and seq — only the predicate string
    changes. After normalization, previously-fragmented facts share a
    conflict key and become visible to canonicalize().
    """
    out: List[Fact] = []
    for f in facts:
        canonical = (
            registry.normalize(f.predicate)
            if registry is not None
            else default_normalize(f.predicate)
        )
        if canonical == f.predicate:
            out.append(f)
        else:
            out.append(
                Fact(
                    entity=f.entity,
                    predicate=canonical,
                    value=f.value,
                    timestamp=f.timestamp,
                    confidence=f.confidence,
                    episode=f.episode,
                    seq=f.seq,
                    id=f.id,
                    expires_at=f.expires_at,
                    derived_from=f.derived_from,
                )
            )
    return out
