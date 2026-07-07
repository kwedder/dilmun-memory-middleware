# Benchmarks

## `bench_vs_chromadb.py` — Dilmun vs ChromaDB

Compares Dilmun's algebraic memory against **ChromaDB** (a widely used vector
store for agent/RAG memory; the same top-k-by-similarity retrieval underlies
Mem0 and LangChain's vector memory).

The benchmark runs ChromaDB's real HNSW index but supplies a deterministic,
offline embedding (a hashing bag-of-words vectorizer), so it needs **no model
download or API key** and is fully reproducible.

### The task

Facts about entities where an attribute is **updated / contradicted over
time** (4 versions each, timestamps shuffled). Then: *what is the current
value?* Highest timestamp = ground truth.

### Running

```bash
py -3 -m pip install chromadb numpy      # numpy is usually already present
py -3 benchmarks/bench_vs_chromadb.py
```

### Representative result (200 entities × 3 attributes × 4 versions)

| metric                     | Dilmun | ChromaDB |
|----------------------------|-------:|---------:|
| write throughput (w/s)     | ~4,900 | ~3,500   |
| mean query latency (ms)    | ~1.0   | ~0.7     |
| current-value accuracy     | **100%** | 25% (vector top-1) |
|                            |        | 100% (metadata + LWW) |

### Interpretation

- **Dilmun is exact by construction.** `canonicalize` resolves
  `(entity, predicate)` conflicts by last-writer-wins, so the current value
  is always returned.
- **Naive vector memory ≈ chance.** All versions of an attribute are
  near-identical in embedding space, so cosine similarity cannot tell the
  current value from a stale one (~1/versions accuracy).
- **The "fix" is to reimplement canonicalize.** ChromaDB reaches 100% only by
  ignoring its vector index and doing a metadata filter on
  `(entity, predicate)` + arg-max timestamp — i.e. LWW by hand, at which point
  the vector store is just key-value storage.
- **Latency/throughput are comparable.** ChromaDB's C++ HNSW gives slightly
  lower query latency; Dilmun writes faster *and* persist to disk (Chroma
  runs in-memory here).

The two systems solve different problems: vector memory answers "what is
semantically related?"; Dilmun answers "what is currently true?"
deterministically. This benchmark isolates the second question.

> Note: on very new Python builds (e.g. 3.14) some `chromadb` transitive deps
> may lag on wheels. Tested with `chromadb==1.5.9` on CPython 3.14.

---

## `bench_semantic_paths.py` — Path 1 (graph) vs Path 2 (MinHash-LSH)

Compares the two ways of adding *semantic retrieval* to Dilmun while staying
inside its logic space, both implemented as deterministic operators over
immutable facts (no learned embeddings, no LLM):

- **Path 1 — GraphIndex:** semantic predicates (`is_a`, `synonym_of`,
  `related_to`) are ordinary facts; retrieval is k-hop reachability over the
  memory graph.
- **Path 2 — MinHashIndex:** MinHash-LSH over character shingles; retrieval is
  candidate lookup by shared LSH bands (approximate Jaccard). A *lexical /
  near-duplicate* method — not synonym-capable.

Two workloads mirror what LoCoMo / LongMemEval / MultiHop-RAG stress:

```bash
py -3 benchmarks/bench_semantic_paths.py
```

### Representative result (3,000 facts, 500 + 500 queries, recall@10)

| workload        | metric   | Graph (P1) | MinHash (P2) |
|-----------------|----------|-----------:|-------------:|
| multi-hop       | recall   | **100.0%** | 0.0%         |
| multi-hop       | query ms | **0.001**  | 0.531        |
| fuzzy (typos)   | recall   | 1.6%       | **84.2%**    |
| fuzzy (typos)   | query ms | **0.001**  | 0.270        |
| build           | ms       | **2.4**    | 889.7        |
| index size      | entries  | **9,000**  | 96,000       |

### Interpretation

- **Multi-hop is graph's home turf and it's decisive** — only reachability can
  chain `person→company→city→country`; MinHash sees no shingle overlap with a
  fact three hops away. Graph is also ~360× cheaper to build and ~500× lower
  query latency, with a ~10× smaller index.
- **The graph is nearly free here.** Published GraphRAG builds cost thousands
  of seconds because of *LLM triple extraction* (RAG 135 s → KG-GraphRAG
  7,702 s in the RAG-vs-GraphRAG study). Dilmun pays none of that: its facts
  already are the edges, so "build" is just adjacency (2.4 ms).
- **Fuzzy near-duplicate is MinHash's niche** — with LSH bands tuned for the
  similarity regime (rows=2), it recovers 84% of typo-corrupted phrases that
  exact word-index seeding misses. The cost is a larger index and higher query
  latency (the recall/cost knob).
- **True open-vocabulary synonymy is benchmarked by neither.** MinHash-LSH is
  lexical (azure ≠ blue share no n-grams); genuine synonymy needs a learned
  embedder, which adds write-time cost and a determinism caveat. Path 1 handles
  it *iff* the `synonym_of` edge exists (ontology coverage).

**Takeaway:** for Dilmun's target — structured, temporal, multi-hop agent
memory (what LoCoMo/LongMemEval weight most) — Path 1 is the efficient default
by a wide margin and costs almost nothing because facts already form the graph.
Path 2 earns a place only as a narrow fuzzy/near-duplicate matcher, best used
HippoRAG-style as a *candidate generator* that proposes `synonym_of`/
`related_to` edges which then fold back into Path 1.
