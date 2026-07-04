# Dilmun

*A deterministic algebra over persistent knowledge states.*

---

## The problem

Modern AI systems forget, duplicate knowledge, and accumulate contradictions
because memory is usually implemented as conversation logs or vector
retrieval. Both are *probabilistic surfaces over text*: they can tell you
what looks similar to a query, but they have no principled account of which
fact is *current*, whether two differently-worded facts are the *same* fact,
or what happens when two states are *merged*.

Dilmun approaches memory differently. It models knowledge as an **immutable,
typed set of facts** governed by **deterministic operators**. Given the same
facts, Dilmun always returns the same state — regardless of insertion order,
retries, or how a fact was phrased.

"Persistent memory for AI agents" is the headline application. The core
contribution is the abstraction underneath it: a deterministic algebra over
persistent knowledge states. Agents, robotics, IoT, and workflow systems are
downstream uses of that abstraction.

---

## Core idea

Memory is not a database.

Memory is a **structured algebraic object**.

A memory state is a finite set of facts:

```
M = { f₁, f₂, ..., fₙ }
```

where each fact is a 5-tuple:

```
f = (e, p, v, t, ν)

  e  entity
  p  predicate      (normalized — see below)
  v  value
  t  timestamp
  ν  confidence valuation in [0, 1]
```

Everything else in Dilmun is a **total, deterministic function** over sets of
these facts.

---

## Design principles

* Facts are **immutable**. Updates append new facts; they never mutate.
* Predicates are **normalized** so paraphrases collapse to one fact.
* Conflicts are resolved **deterministically**, not by similarity.
* Core transformations are **idempotent**.
* Stale knowledge is removed by a **forgetting** operator, not ad-hoc deletion.
* Retrieval is **structured and reproducible**, not probabilistic guessing.

---

## Install

```bash
pip install dilmun
```

Pure-Python, no required dependencies. `numpy` is used only by the benchmark.

---

## Quick start

```python
from dilmun import DilmunMemory

memory = DilmunMemory("./vault")

memory.open_episode("chat_001")

memory.write_fact(
    entity="user",
    predicate="favorite_color",
    value="blue",
    confidence=0.95,
)

memory.write_fact(
    entity="user",
    predicate="location",
    value="Miami",
)

context = memory.get_context()   # canonical, scored, deterministic

memory.close_episode()
```

---

## The memory algebra

Dilmun is defined by a small set of operators over memory states. Each has a
precise signature and precise behaviour. For the full formal treatment —
operators specified by their properties, the reduction-system analysis, and
the honest status of every claim — see **[MODEL.md](MODEL.md)**. In one line:

> Dilmun is a **deterministic state-rewrite algebra over immutable labeled
> graphs** — not a ring, not a lattice, not a category. Where a classical
> structure genuinely emerges (the merge semilattice), it is named; where it
> does not, it is not claimed.

| Operator | Signature | What it does |
|---|---|---|
| **Normalize** | `N(M, registry) → M` | Map predicate aliases onto canonical predicates |
| **Canonicalize** | `C(M) → M` | Collapse conflicting facts to one representative each |
| **Forget** | `F(M) → M` | Project memory onto its still-valid facts |
| **Compose** | `comp(f₁, f₂) → f` | Derive a fact by path composition on the graph |
| **Merge** | `merge(M₁, M₂) → M` | Combine two states: `C(M₁ ∪ M₂)` |
| **Promote** | `promote(f): Mᵢ → M₀` | Lift an episode fact into global memory |
| **Retrieve** | `retrieve(M) → [f…]` | Rank facts by a deterministic score |

The rest of this section defines each one.

### 1. Confidence valuation

```
ν : M → [0, 1]
```

Assigns reliability to each fact. Higher = stronger evidence. Used for
ranking and as a tie-breaker in canonicalization.

### 2. Predicate normalization — `N`

This is what makes the rest of the algebra stable, and it is the piece most
memory systems skip.

Without normalization, these are **four different facts**:

```
(A, owns,        B)
(A, possesses,   B)
(A, has,         B)
(A, is owner of, B)
```

so no conflict is ever detected and memory fragments. Dilmun applies two
layers of normalization:

* **Default normalization** — casefold, trim, collapse whitespace/hyphens to
  underscores. Applied to *every* predicate. `"is owner of" → "is_owner_of"`.
* **Registry normalization** — an explicit alias → canonical map on top:

```python
from dilmun import DilmunMemory, PredicateRegistry

reg = PredicateRegistry().register("OWNS", "owns", "possesses", "has", "is owner of")

memory = DilmunMemory("./vault", predicates=reg)
memory.write_fact("A", "possesses", "B")   # stored as (A, OWNS, B)
```

Now `(A, owns, B)` and `(A, possesses, B)` are the *same* fact, and
canonicalization can act on them. Normalization is the precondition that
turns the operators below from "a database with equations" into an algebra.

### 3. Canonicalization — `C`

Two facts **conflict** when they share `(entity, predicate)` but differ in
value:

```
(user, city, Miami)
(user, city, Orlando)
```

Canonicalization keeps one representative per `(entity, predicate)`:

```
C(M) = ⋃  select(e, p)
      (e,p)

select(e, p):
    1. highest timestamp        (most recent wins)
    2. highest confidence        (tie-break)
    3. stable insertion order    (final tie-break — total order)
```

Because `select` imposes a *total* order on each conflict group, `C` is:

* **idempotent** — `C(C(M)) = C(M)`
* **deterministic** — `M₁ = M₂ ⇒ C(M₁) = C(M₂)`

(Both are covered by tests in `tests/test_operators.py`. These are
test-backed guarantees, not machine-checked proofs — see Roadmap.)

### 4. Forgetting — `F`

Forgetting is **not deletion**. It is a *projection* of memory onto the
subset of still-valid facts:

```
F : M → M      F(F(M)) = F(M)
```

A fact leaves memory when it is:

* expired (`t` past its TTL),
* below a confidence floor, or
* under contradiction pressure (optional policy: it lost canonicalization to
  a fact with a different value).

`F` is idempotent: reapplying it changes nothing.

### 5. Episode-partitioned memory

Memory is partitioned into a global component and per-episode components:

```
M = M₀ ∪ M₁ ∪ … ∪ M_k

  M₀   global memory
  Mᵢ   episode memory
```

Writes inside an open episode land in that episode; writes outside land in
`M₀`. Retrieval sees `M₀ ∪ M_active`, so **episodes are isolated by default**
and cross-episode promotion is **explicit**:

```python
memory.open_episode("session_42")
f = memory.write_fact("user", "timezone", "EST")   # lives in session_42
memory.close_episode()

memory.promote(f)   # now visible globally, in M₀
```

> Note on terminology: this is a *partition* of memory by context, not a
> graded ring — there is no grading map or graded product defined here. We
> call it episode partitioning to keep the claim honest.

### 6. Memory graph & composition — `comp`

Facts induce a directed labeled graph:

```
Alice ──likes──▶ Coffee ──served_at──▶ Cafe
      nodes = entities/values,  edges = predicates
```

Composition derives a new fact by walking an edge pair, valid when
`f₁.value == f₂.entity`:

```
(A, likes, B) ∘ (B, category, C)  =  (A, likes_category, C)
```

The derived fact carries `ν(f₁)·ν(f₂)`, the newer timestamp, and provenance
back to both parents. This is path composition over the graph — a structured
alternative to tensor/embedding combination.

### 7. Retrieval

Retrieval is a **deterministic pipeline**, not approximate search:

```
candidate generation   (M₀ ∪ M_active)
        ↓
forgetting F           (drop expired / low-confidence)
        ↓
canonicalization C     (resolve conflicts)
        ↓
deterministic ranking  score(f) = w₁·ν(f) + w₂·recency + w₃·centrality
```

Ties in the score break on newer timestamp, then insertion order, so the
returned list is fully reproducible. `retrieve` replaces embedding similarity
with a structured, explainable score.

---

## Benchmarks

`benchmarks/benchmark.py` compares Dilmun against a TF-IDF cosine-similarity
memory (`benchmarks/vector_baseline.py`) — the classic embedding-retrieval
pattern, differing from a neural memory only in the embedding function.
Everything is seeded and reproducible:

```bash
python benchmarks/benchmark.py
```

Results (seed `20260704`, Python 3.14, single run):

| Task | Metric | Dilmun | Vector (TF-IDF) |
|---|---|---:|---:|
| **Current-value recall** after 5 updates/entity | correct = latest value | **100.0%** | 24.5% |
| **Determinism** across 8 insertion-order shuffles | answers stable | **100.0%** | 96.7% |
| **Dedup** of one fact under 4 predicate aliases | facts stored (200 entities) | **200 (1×)** | 800 (4×) |
| | redundant hits in top-4 | **0** | 4 / 4 |
| **Write throughput** (2 000 facts) | facts / sec | 8 450 | **149 178** |
| **Query latency** (500 queries) | ms / query | 0.567 | **0.167** |

**What the numbers say.** Where the task is "which fact is *true now*," Dilmun
is correct by construction and the vector store is near chance (24.5%),
because cosine similarity has no notion of recency — the current and stale
versions of a fact look equally similar to a query. Normalization removes the
4× duplication that paraphrasing creates in the vector store. Determinism is
the subtler result: even this *exact* baseline flips ~3.3% of answers under
reordering; approximate-nearest-neighbor indexes over neural embeddings are
typically less stable, not more.

**What the numbers do not say.** The vector baseline is faster here — it runs
in memory while Dilmun persists every write to disk and scans on query.
Dilmun trades raw throughput for durability and determinism; neither store is
performance-tuned, so treat latency as order-of-magnitude only.

### Which algebraic framing is earned?

A second benchmark (`benchmarks/algebra_properties.py`) tests, over 3 000
random states, which mathematical properties Dilmun's operators actually
satisfy — deciding empirically between the "rewrite system" and "CRDT" lenses
rather than asserting either:

| Property | Lens | Holds |
|---|---|---:|
| Determinism of canonicalization | — | 100% |
| Idempotence of `N`, `C`, `F` | — | 100% |
| **Confluence of core `{Normalize, Canonicalize}`** | rewrite system | **100%** |
| **Confluence of full `{Normalize, Canonicalize, Forget}`** | rewrite system | **39.7%** |
| Merge idempotent / commutative / associative | semilattice / CRDT | 100% |

The verdict: the **normalizing core is a confluent reduction system** (unique
canonical normal form regardless of order), and **merge is a genuine
join-semilattice / LWW-Map CRDT**. But **Forget breaks confluence** — the
confidence floor and the recency ranking disagree about which fact survives,
so `C` and `F` do not commute. Dilmun handles this by fixing the evaluation
order (`C ∘ F`) rather than pretending the rule set is confluent. Full
derivation, the counterexample, and the honest status of each claim are in
[MODEL.md](MODEL.md) §5–§7.

---

## Limitations

Being honest about where this abstraction does and doesn't help:

* **Dilmun does not do semantic retrieval.** It matches on normalized
  structure, not meaning. A query for `"vehicle"` will not find `(A, owns,
  car)` unless a registry or synonym layer connects them. Vector memory is
  the better tool when queries are fuzzy and facts are unstructured text.
* **Normalization is only as good as its registry.** Out-of-registry
  paraphrases still fragment. Default normalization handles casing and
  spacing, not synonymy. Automatic predicate discovery is future work.
* **Facts must be extracted first.** Dilmun assumes you already have
  `(e, p, v)` triples. Turning raw conversation into good triples (entity
  resolution, predicate choice) is upstream of Dilmun and is where most real
  error lives.
* **The benchmark is a micro-benchmark**, not a standardized suite
  (LoCoMo, LongMemEval, …), and it uses TF-IDF vectors rather than a neural
  encoder. A neural encoder would change absolute similarity numbers, but not
  the structural findings: similarity-only retrieval has no intrinsic recency
  rule, no dedup across paraphrase, and no guaranteed determinism. Notably, a
  vector store *can* recover current-value recall by attaching recency
  metadata and sorting by it — but that recency-plus-tiebreak rule is exactly
  canonicalization. The claim here is not that Dilmun is magic; it is that
  these properties should be intrinsic to the memory model rather than bolted
  on per query.
* **Guarantees are test-backed, not proven.** Idempotence, determinism, and
  merge commutativity/associativity are checked by the test suite, not by a
  proof assistant.

---

## Storage backends

* **JSON vault** (default) — append-only `facts.jsonl` + `episodes.json`
* **SQLite** — single-file database

```python
DilmunMemory("./vault", backend="json")     # default
DilmunMemory("./vault", backend="sqlite")
```

Both persist the same immutable facts and produce identical canonical state
(`tests/test_memory.py::test_backends_agree`). Planned: PostgreSQL / DuckDB,
distributed CRDT memory.

---

## Formal properties

Properties currently **verified by the test suite** (`tests/`):

* **Canonicalization** — idempotent, deterministic, conflict-resolving.
* **Forgetting** — idempotent projection, stable under repeated application.
* **Merge** — commutative and associative (`merge(A,B) = merge(B,A)`,
  `merge(merge(A,B),C) = merge(A,merge(B,C))`).
* **Episodes** — partitioned state, non-interfering updates by default.
* **Backends** — JSON and SQLite yield identical canonical context.

These are stated as *test-backed*, not machine-checked. See Roadmap.

---

## Applications

Downstream uses of the algebra:

* Long-horizon AI agents
* Robotics memory systems
* IoT device cognition layers
* Multi-agent coordination
* Persistent research assistants
* Workflow automation systems

---

## Roadmap

* Automatic predicate discovery / synonym induction
* Provenance tracking per fact (partially present via `derived_from`)
* Typed predicate system with value constraints
* Temporal decay functions for `ν`
* Query planner over the memory graph
* Distributed memory synchronization (CRDT-based)
* **Formal verification** of the canonicalization, forgetting, and merge
  properties in a proof assistant — currently these are only test-backed.

---

## Mathematical inspiration (not foundation)

Dilmun borrows a *philosophy* from ring theory — not a theorem. Wedderburn's
little theorem (every finite division ring is commutative), and the exposition
in Kaczynski's 1964 note "Another Proof of Wedderburn's Theorem," share a
shape of argument worth stealing: **a structure that looks maximally free
turns out to be rigid** — finiteness alone forces a non-commutative object to
commute.

Dilmun aims at the analogous move for *memory*: messy, redundant,
contradictory input is forced — by immutability plus deterministic reduction —
into a rigid canonical form, and operations that look order-dependent (merge)
turn out to be order-independent. That is the entire connection, and it is an
**analogy**. Dilmun's objects are labeled graphs and rewrite operators, not
division rings; we do not claim Wedderburn as a mechanism or a correctness
argument. The algebra in [MODEL.md](MODEL.md) is meant to stand on its own
definitions. (Earlier drafts named a "Wedderburn-Kasczinski" resolution rule
in the code; that was decorative and has been removed — the rule is
last-write-wins with a total-order tie-break, described plainly.)

## Philosophy

Dilmun is not an embedding database or a chatbot plugin. It is a
**deterministic state-rewrite algebra over persistent knowledge states** — a
formal model of machine memory that remembers, reconciles, and evolves
knowledge over time. The AI applications are what you build *on top* of that
model.

---

## License

MIT
