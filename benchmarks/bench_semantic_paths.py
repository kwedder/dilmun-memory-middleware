"""
Benchmark: Path 1 (semantics-as-facts, graph reachability) vs
           Path 2 (semantic hashing, MinHash-LSH) for semantic retrieval
           inside Dilmun's logic space.

Both indices operate over immutable (entity, predicate, value) facts and are
fully deterministic — no learned embeddings, no LLM. They model the two
mechanisms discussed for adding semantic retrieval to Dilmun:

    Path 1  GraphIndex   — reserve semantic predicates (is_a, synonym_of,
                           related_to) as ordinary facts; retrieval is k-hop
                           reachability over the memory graph (reuses the
                           build_graph / compose / derive machinery).
    Path 2  MinHashIndex — MinHash-LSH over character shingles of each fact;
                           retrieval is candidate lookup by shared LSH bands,
                           ranked by band overlap (approx Jaccard). The classic
                           data-independent semantic-hashing mechanism.

Two workloads mirror what popular memory benchmarks stress (LoCoMo /
LongMemEval / MultiHop-RAG):

    A. multi-hop  — answer requires chaining 3 relations (graph's home turf)
    B. fuzzy      — query is a typo-corrupted phrase, no entity handle
                    (near-duplicate matching; MinHash-LSH's home turf)

Note on scope: MinHash-LSH is a *lexical / near-duplicate* method (character
shingles), so B tests surface robustness, not true synonymy. Genuine
open-vocabulary synonymy ("azure" == "blue") needs a learned embedder — extra
write-time cost and a determinism caveat — and is discussed, not benchmarked,
here (no torch wheels on this CPython build).

Reported per index/workload: build time, index size (postings/edges),
mean query latency, and recall@k.
"""

from __future__ import annotations

import random
import time
from collections import defaultdict
from typing import Dict, List, Set, Tuple

SEED = 11
N_ENTITIES = 500
BUDGET = 10          # retrieval budget k (recall@k)

Fact = Tuple[str, str, str]          # (entity, predicate, value)


# ==========================================================================
# workloads
# ==========================================================================

# pool of rare-ish words to build near-unique 3-word phrases for workload B
WORDS = [
    "quixotic", "zephyr", "lattice", "marigold", "obsidian", "cascade",
    "nimbus", "verdant", "cobalt", "thistle", "harbor", "ember", "willow",
    "granite", "meadow", "cinder", "sable", "quartz", "juniper", "onyx",
    "saffron", "brindle", "fathom", "gossamer", "halcyon", "isthmus",
    "kestrel", "lyric", "mistral", "nectar", "opal", "plume", "russet",
    "tundra", "umber", "vellum", "wisteria", "yarrow", "zenith", "amber",
]


def _typo(word: str, rng: random.Random) -> str:
    """One random single-character mutation (swap/replace/drop)."""
    if len(word) < 3:
        return word
    i = rng.randrange(len(word))
    kind = rng.choice(("swap", "replace", "drop"))
    if kind == "swap" and i < len(word) - 1:
        return word[:i] + word[i + 1] + word[i] + word[i + 2:]
    if kind == "drop":
        return word[:i] + word[i + 1:]
    return word[:i] + rng.choice("abcdefghijklmnopqrstuvwxyz") + word[i + 1:]


def build_workloads():
    rng = random.Random(SEED)
    facts: List[Fact] = []

    # -- A. multi-hop chains: person -> company -> city -> country ----------
    multihop_queries = []          # (seed_entity, answer_fact)
    for i in range(N_ENTITIES):
        p, c, city, country = (
            f"person_{i}", f"company_{i}", f"city_{i}", f"country_{i}"
        )
        facts += [
            (p, "works_at", c),
            (c, "located_in", city),
            (city, "in_country", country),
            # noise attributes that share the person's name/token
            (p, "age", str(rng.randint(20, 70))),
            (p, "hobby", rng.choice(["chess", "surf", "piano", "hiking"])),
        ]
        answer = (city, "in_country", country)     # reachable only in 3 hops
        multihop_queries.append((p, answer))

    # -- B. fuzzy: near-unique phrase, queried with typos, no handle -------
    fuzzy_queries = []             # (query_text, answer_fact)
    for i in range(N_ENTITIES):
        u = f"note_{i}"
        phrase = " ".join(rng.sample(WORDS, 3))    # near-unique among N
        facts.append((u, "text", phrase))
        typoed = " ".join(_typo(w, rng) for w in phrase.split())
        fuzzy_queries.append((typoed, (u, "text", phrase)))

    return facts, multihop_queries, fuzzy_queries


# ==========================================================================
# Path 1 — graph reachability over semantic facts
# ==========================================================================

class GraphIndex:
    """k-hop reachability over the memory graph. Semantic predicates are
    just facts, so synonym bridging is graph traversal, and multi-hop
    answers are found by chaining edges."""

    def __init__(self, facts: List[Fact]):
        t0 = time.perf_counter()
        self.out: Dict[str, List[Fact]] = defaultdict(list)   # node -> facts
        self.token_index: Dict[str, Set[str]] = defaultdict(set)  # word->nodes
        for f in facts:
            e, p, v = f
            self.out[e].append(f)
            # word-level inverted index so exact-match seeding is a fair
            # competitor on surface queries (entity words + value words)
            for word in (e, *str(v).split()):
                self.token_index[word].add(e)
        self.build_s = time.perf_counter() - t0
        self.size = sum(len(v) for v in self.out.values()) + sum(
            len(v) for v in self.token_index.values()
        )

    def _seed(self, terms: List[str]) -> Set[str]:
        seeds: Set[str] = set()
        for t in terms:
            seeds |= self.token_index.get(t, set())
        return seeds

    def reach(self, seeds: Set[str], budget: int) -> List[Fact]:
        """BFS outward, collecting facts in breadth order up to budget."""
        seen_nodes: Set[str] = set(seeds)
        frontier = list(seeds)
        collected: List[Fact] = []
        while frontier and len(collected) < budget:
            nxt: List[str] = []
            for node in frontier:
                for f in self.out.get(node, ()):
                    collected.append(f)
                    if len(collected) >= budget:
                        break
                    target = f[2]
                    if target not in seen_nodes:
                        seen_nodes.add(target)
                        nxt.append(target)
                if len(collected) >= budget:
                    break
            frontier = nxt
        return collected

    def query_multihop(self, seed_entity: str, budget: int) -> List[Fact]:
        return self.reach({seed_entity}, budget)

    def query_terms(self, terms: List[str], budget: int) -> List[Fact]:
        return self.reach(self._seed(terms), budget)


# ==========================================================================
# Path 2 — MinHash-LSH over character shingles
# ==========================================================================

_P = (1 << 61) - 1


class MinHashIndex:
    def __init__(self, facts: List[Fact], num_perm: int = 64, rows: int = 2,
                 ngram: int = 3):
        rng = random.Random(SEED)
        self.hashes = [(rng.randrange(1, _P), rng.randrange(0, _P))
                       for _ in range(num_perm)]
        self.num_perm, self.rows, self.ngram = num_perm, rows, ngram
        self.bands = num_perm // rows
        self.fact_by_id: Dict[int, Fact] = {}
        self.postings: Dict[Tuple, List[int]] = defaultdict(list)

        t0 = time.perf_counter()
        for fid, f in enumerate(facts):
            self.fact_by_id[fid] = f
            sig = self._sig(self._shingles(self._text(f)))
            for band, key in self._band_keys(sig):
                self.postings[(band, key)].append(fid)
        self.build_s = time.perf_counter() - t0
        self.size = sum(len(v) for v in self.postings.values())

    @staticmethod
    def _text(f: Fact) -> str:
        return f"{f[0]} {f[1]} {f[2]}".lower().replace("_", " ")

    def _shingles(self, text: str) -> Set[int]:
        text = f"  {text}  "
        return {hash(text[i:i + self.ngram]) & _P
                for i in range(len(text) - self.ngram + 1)}

    def _sig(self, shingles: Set[int]) -> List[int]:
        if not shingles:
            return [0] * self.num_perm
        return [min(((a * s + b) % _P) for s in shingles)
                for a, b in self.hashes]

    def _band_keys(self, sig: List[int]):
        for band in range(self.bands):
            sl = tuple(sig[band * self.rows:(band + 1) * self.rows])
            yield band, sl

    def query(self, text: str, budget: int) -> List[Fact]:
        sig = self._sig(self._shingles(text.lower().replace("_", " ")))
        overlap: Dict[int, int] = defaultdict(int)
        for band, key in self._band_keys(sig):
            for fid in self.postings.get((band, key), ()):
                overlap[fid] += 1
        ranked = sorted(overlap, key=lambda fid: -overlap[fid])
        return [self.fact_by_id[fid] for fid in ranked[:budget]]


# ==========================================================================
# harness
# ==========================================================================

def recall_at_k(retrieved: List[Fact], answer: Fact) -> int:
    return 1 if answer in retrieved else 0


def evaluate(name, fn, queries) -> dict:
    hits, latencies = 0, []
    for q, answer in queries:
        t0 = time.perf_counter()
        got = fn(q)
        latencies.append(time.perf_counter() - t0)
        hits += recall_at_k(got, answer)
    return {
        "name": name,
        "recall": hits / len(queries),
        "mean_query_ms": 1000 * sum(latencies) / len(latencies),
    }


def main():
    facts, mh_q, fz_q = build_workloads()
    print(f"KB: {len(facts)} facts")
    print(f"    {len(mh_q)} multi-hop queries, {len(fz_q)} fuzzy queries")
    print(f"    budget = recall@{BUDGET}\n")

    graph = GraphIndex(facts)
    mh = MinHashIndex(facts)

    print(f"{'index':<14}{'build ms':>10}{'index size':>12}")
    print("-" * 36)
    print(f"{'GraphIndex':<14}{graph.build_s*1000:>10.1f}{graph.size:>12,}")
    print(f"{'MinHashIndex':<14}{mh.build_s*1000:>10.1f}{mh.size:>12,}")
    print()

    # -- Workload A: multi-hop --------------------------------------------
    g_mh = evaluate("graph", lambda q: graph.query_multihop(q, BUDGET), mh_q)
    # MinHash gets the raw seed entity as its query text (its best case)
    h_mh = evaluate("minhash", lambda q: mh.query(q, BUDGET), mh_q)

    # -- Workload B: fuzzy (typo-corrupted, no handle) --------------------
    g_fz = evaluate("graph", lambda q: graph.query_terms(q.split(), BUDGET), fz_q)
    h_fz = evaluate("minhash", lambda q: mh.query(q, BUDGET), fz_q)

    print(f"{'workload':<16}{'metric':<16}{'Graph (P1)':>12}{'MinHash (P2)':>14}")
    print("-" * 58)
    print(f"{'multi-hop':<16}{'recall@'+str(BUDGET):<16}"
          f"{g_mh['recall']:>11.1%}{h_mh['recall']:>14.1%}")
    print(f"{'':<16}{'query ms':<16}"
          f"{g_mh['mean_query_ms']:>12.3f}{h_mh['mean_query_ms']:>14.3f}")
    print(f"{'fuzzy (typos)':<16}{'recall@'+str(BUDGET):<16}"
          f"{g_fz['recall']:>11.1%}{h_fz['recall']:>14.1%}")
    print(f"{'':<16}{'query ms':<16}"
          f"{g_fz['mean_query_ms']:>12.3f}{h_fz['mean_query_ms']:>14.3f}")
    print()
    print("reading:")
    print("  * multi-hop: only graph reachability can chain person->company")
    print("    ->city->country; MinHash sees no shingle overlap with the")
    print("    3-hops-away answer fact.")
    print("  * fuzzy: every query word is typo-corrupted, so exact word-index")
    print("    seeding (graph) mostly misses; MinHash char-shingles survive")
    print("    single-char edits and recover the near-duplicate fact.")


if __name__ == "__main__":
    main()
