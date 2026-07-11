"""
Binding memory — clique-bound associative recall with a confabulation guard.

DRAFT / not yet wired into the package (`dilmun/__init__.py` is untouched).
Import directly:  ``from dilmun.binding import BindingMemory``.

Motivation (measured, not assumed)
-----------------------------------
An isolated head-to-head of the three candidate robustness primitives
(Gripon-Berrou cliques, morphological AM, entropic register) on one common
task produced two findings that this module operationalizes:

* **Reconstruction (fill missing parts of a memory):** clique binding was the
  strongest and the most load-tolerant.
* **Veridicality (tell a genuine memory from a synthesized one):** a memory that
  stores only *which values exist* (marginals) certifies fabricated
  *combinations* as real at every load. Only a memory that stores *relationships*
  can reject a "ghost memory". i.e. **veridicality requires binding** — the truth
  signal is relational, not token-level.

So Dilmun's binding memory stores co-occurrence: the ``(predicate, value)`` cells
observed together for one entity form a **clique** in a single undirected graph.
Superimposing many records' cliques gives a deterministic structure that supports
two operations:

    reconstruct(known, targets)  — recover missing cells from present ones (R1)
    veridicality(cells)          — is this bundle a genuinely stored clique? (R2)

Everything here is a pure, deterministic function of the stored edge set. No
learned parameters, no randomness; equal inputs yield identical outputs.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .fact import Fact
from .operators import canonicalize

# A binding node is a (predicate, value) cell.
Node = Tuple[str, Any]


def _pair(a: Node, b: Node) -> Tuple[Node, Node]:
    """Canonical (order-independent) key for an undirected edge."""
    return (a, b) if repr(a) <= repr(b) else (b, a)


class BindingMemory:
    """A clique-bound associative store over ``(predicate, value)`` cells.

    A *record* is a set of cells observed together (by default, the facts of one
    ``(entity, episode)``). Storing a record marks every pair of its cells as
    bound. The store therefore remembers *which cells co-occurred*, which is the
    substrate for both relational recovery and confabulation detection.
    """

    def __init__(self) -> None:
        self._edge_weight: Dict[Tuple[Node, Node], int] = defaultdict(int)
        self._nodes: Dict[Node, int] = defaultdict(int)          # cell -> support
        self._vocab: Dict[str, set] = defaultdict(set)           # predicate -> values
        self._records = 0

    # -- construction -------------------------------------------------------

    def store_record(self, cells: Iterable[Node]) -> None:
        """Bind every pair of cells in one co-observed record (a clique)."""
        cells = list(dict.fromkeys(cells))          # de-dup, keep order
        for (pred, val) in cells:
            self._nodes[(pred, val)] += 1
            self._vocab[pred].add(val)
        for i in range(len(cells)):
            for j in range(i + 1, len(cells)):
                self._edge_weight[_pair(cells[i], cells[j])] += 1
        self._records += 1

    def store_facts(
        self,
        facts: Iterable[Fact],
        *,
        key: Callable[[Fact], Any] = lambda f: (f.entity, f.episode),
    ) -> None:
        """Group facts into records by ``key`` and store each as a clique.

        Facts in a group are canonicalized first, so a record carries at most
        one value per predicate (a consistent snapshot).
        """
        groups: Dict[Any, List[Fact]] = defaultdict(list)
        for f in facts:
            groups[key(f)].append(f)
        for _, group in sorted(groups.items(), key=lambda kv: repr(kv[0])):
            snapshot = canonicalize(group)
            self.store_record((f.predicate, f.value) for f in snapshot)

    # -- helpers ------------------------------------------------------------

    def bound(self, a: Node, b: Node) -> bool:
        """Whether cells ``a`` and ``b`` were ever observed together."""
        return self._edge_weight.get(_pair(a, b), 0) > 0

    def knows_value(self, predicate: str, value: Any) -> bool:
        return value in self._vocab.get(predicate, ())

    # -- R2: veridicality / confabulation guard -----------------------------

    def veridicality(self, cells: Iterable[Node]) -> float:
        """Fraction of cell-pairs that are actually bound in the store, in
        [0, 1]. 1.0 means every pair co-occurred (a complete stored clique);
        a novel value or an un-observed combination drags it below 1.0.

        This is the graded truth signal Dilmun surfaces instead of hiding.
        A single cell (no pairs) scores 1.0 iff that cell exists, else 0.0.
        """
        cells = list(dict.fromkeys(cells))
        if not cells:
            return 1.0
        if any(self._nodes.get(c, 0) == 0 for c in cells):
            return 0.0                                # a cell never stored at all
        if len(cells) == 1:
            return 1.0
        total = present = 0
        for i in range(len(cells)):
            for j in range(i + 1, len(cells)):
                total += 1
                if self.bound(cells[i], cells[j]):
                    present += 1
        return present / total

    def is_genuine(self, cells: Iterable[Node], *, threshold: float = 1.0) -> bool:
        """Accept a bundle as a genuine memory iff its veridicality meets
        ``threshold`` (default: a complete clique). Rejects both novel values
        and novel *combinations* of seen values (ghost memories)."""
        return self.veridicality(cells) >= threshold

    # -- R1: reconstruction (fill missing cells) ----------------------------

    def reconstruct(
        self,
        known: Dict[str, Any],
        targets: Sequence[str],
        *,
        min_binding: float = 1.0,
    ) -> Dict[str, Optional[Any]]:
        """Recover the value of each missing ``predicate`` in ``targets`` from
        the ``known`` cells, by clique decoding.

        A candidate value v is accepted only if the *completed bundle*
        ``known ∪ {(p, v)}`` has veridicality >= ``min_binding`` (default 1.0: a
        complete clique). This deliberately also requires the known cells to be
        bound to *each other* — so a "context" that never co-occurred yields no
        value (the memory abstains rather than confabulate from a spurious,
        pairwise-only match). Otherwise the slot is left ``None``.

        Deterministic tie-break: higher total edge weight to the known cells,
        then value sorted by ``repr``.
        """
        known_cells: List[Node] = [(p, v) for p, v in known.items()]
        out: Dict[str, Optional[Any]] = {}
        for p in targets:
            best_v: Optional[Any] = None
            best_key: Tuple[float, int, str] = (min_binding, -1, "")
            for v in sorted(self._vocab.get(p, ()), key=repr):
                cell = (p, v)
                bundle = known_cells + [cell]
                vd = self.veridicality(bundle)
                if vd < min_binding:
                    continue
                weight = sum(
                    self._edge_weight.get(_pair(cell, k), 0) for k in known_cells
                )
                key = (vd, weight, repr(v))
                if best_v is None or key > best_key:
                    best_key, best_v = key, v
            out[p] = best_v
        return out

    # -- introspection ------------------------------------------------------

    @property
    def num_records(self) -> int:
        return self._records

    @property
    def num_edges(self) -> int:
        return len(self._edge_weight)

    def __repr__(self) -> str:
        return (
            f"BindingMemory(records={self._records}, cells={len(self._nodes)}, "
            f"edges={len(self._edge_weight)})"
        )
