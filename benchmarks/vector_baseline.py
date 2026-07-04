"""
A self-contained vector-memory baseline for the benchmark.

This is a classic TF-IDF + cosine-similarity retrieval store: each fact is
flattened to the document "entity predicate value", embedded as an L2-
normalized TF-IDF vector, and recalled by nearest cosine neighbour. It is
the same shape as an embedding-based memory (RAG-style) — only the
embedding function differs. Using TF-IDF instead of a neural encoder keeps
the benchmark dependency-free and fully reproducible; see the Limitations
section of the README for what that does and does not change.

Only numpy is required.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> List[str]:
    return _TOKEN.findall(text.lower())


class VectorMemory:
    """TF-IDF cosine-similarity memory over (entity, predicate, value) facts."""

    def __init__(self) -> None:
        self._docs: List[Dict] = []          # {entity, predicate, value, tokens}
        self._vocab: Dict[str, int] = {}
        self._idf: Optional[np.ndarray] = None
        self._matrix: Optional[np.ndarray] = None
        self._dirty = True

    def write_fact(self, entity: str, predicate: str, value: str) -> None:
        text = f"{entity} {predicate} {value}"
        self._docs.append({
            "entity": entity,
            "predicate": predicate,
            "value": value,
            "tokens": tokenize(text),
        })
        self._dirty = True

    # -- index build ---------------------------------------------------------

    def _vectorize(self, tokens: List[str]) -> np.ndarray:
        vec = np.zeros(len(self._vocab), dtype=np.float64)
        tf: Dict[int, int] = defaultdict(int)
        for tok in tokens:
            idx = self._vocab.get(tok)
            if idx is not None:
                tf[idx] += 1
        for idx, count in tf.items():
            vec[idx] = count * self._idf[idx]
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def build_index(self) -> None:
        """Fit vocabulary + IDF over the corpus and embed every document."""
        self._vocab = {}
        for doc in self._docs:
            for tok in doc["tokens"]:
                if tok not in self._vocab:
                    self._vocab[tok] = len(self._vocab)

        n = len(self._docs)
        df = np.zeros(len(self._vocab), dtype=np.float64)
        for doc in self._docs:
            for tok in set(doc["tokens"]):
                df[self._vocab[tok]] += 1
        # smoothed idf
        self._idf = np.log((1 + n) / (1 + df)) + 1.0

        self._matrix = np.vstack([self._vectorize(d["tokens"]) for d in self._docs]) \
            if self._docs else np.zeros((0, len(self._vocab)))
        self._dirty = False

    # -- retrieval -----------------------------------------------------------

    def _query_vec(self, query_text: str) -> np.ndarray:
        return self._vectorize(tokenize(query_text))

    def top_k(self, query_text: str, k: int = 5) -> List[Dict]:
        """Return the k documents with highest cosine similarity.

        Ties are broken by np.argsort's stable order (insertion order),
        which is exactly why the store is sensitive to insertion order.
        """
        if self._dirty:
            self.build_index()
        if not self._docs:
            return []
        q = self._query_vec(query_text)
        sims = self._matrix @ q
        # stable descending sort: negate then argsort keeps ties in insert order
        order = np.argsort(-sims, kind="stable")[:k]
        return [self._docs[i] for i in order]

    def recall_value(self, entity: str, predicate: str) -> Optional[str]:
        """The store's best answer to 'what is (entity, predicate)?' —
        the value of the top-1 cosine match for the intent 'entity predicate'."""
        hits = self.top_k(f"{entity} {predicate}", k=1)
        return hits[0]["value"] if hits else None

    def distinct_stored(self) -> int:
        return len(self._docs)
