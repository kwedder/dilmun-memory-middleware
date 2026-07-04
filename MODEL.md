# The Dilmun Memory Algebra

*A formal model of the objects and operators Dilmun implements.*

This document defines Dilmun on its own terms rather than borrowing a
classical structure (ring, lattice, category) wholesale. Where a classical
structure genuinely emerges, it is named and its status is stated honestly:
**proved by argument**, **test-backed** (checked empirically, not machine-
proved), or **open / goal**.

If Dilmun needs a one-line classification, it is this:

> **A deterministic state-rewrite algebra over immutable labeled graphs.**

The state is a finite graph of immutable facts; the algebra is a set of
operators that rewrite the state toward canonical normal forms while
preserving explicit invariants (determinism, idempotence, semilattice merge).

### What is actually established (read this first)

Every claim below carries an explicit confidence level. In brief:

| | Guarantee | Where |
|---|---|---|
| **Proved** | Merge is a semilattice (CvRDT) join · `K=C∘F` is an idempotent projection · `C` and `F` cannot commute · replica convergence · termination | §5–§6 |
| **Test-backed** | Determinism · idempotence of `N`/`C`/`F` · confluence of `{N,C}` · 6-replica convergence (100%) | §5–§7 |
| **False by design** | Full `{N,C,F}` confluence (~40%) — resolved by fixed evaluation order, not pretended away | §5 |
| **Inspiration only** | Wedderburn / ring theory — an analogy, never a foundation | §8 |

The full status table with exact wording is §7. "Test-backed" means checked
empirically over randomized inputs, not machine-checked.

---

## 0. The object

A **Dilmun memory algebra** is a tuple

```
D = (M, Σ, O, ν, Π)
```

* `M` — a memory state (a finite set of immutable facts)
* `Σ` — the predicate registry (a finite canonical predicate alphabet)
* `O` — the memory operators
* `ν` — the confidence valuation
* `Π` — the episode partition

Each component is defined below.

---

## 1. Knowledge model

### Facts

A memory state is a finite set of immutable facts:

```
M = { f₁, f₂, …, fₙ }
```

A fact is a tuple

```
f = (e, p, v, t, c, m)

  e  entity              (a node label)
  p  predicate ∈ Σ       (a canonical edge label)
  v  value               (a node label)
  t  timestamp ∈ ℝ≥0
  c  confidence ∈ [0,1]  (= ν(f))
  m  metadata            (optional provenance: source, derived_from, episode, seq)
```

Facts are **immutable**. There is no update-in-place; revising knowledge
appends a new fact. The implementation carries `m` as the fields `episode`,
`seq` (a stable insertion index), and `derived_from` (provenance for facts
produced by composition).

### Memory as a labeled graph

Every fact is a labeled directed edge `e —p→ v`, so a state `M` denotes a
finite **labeled directed multigraph**

```
G(M) = (V, E),   V = entities ∪ values,   E = { e —p→ v : (e,p,v,…) ∈ M }
```

This is the object the operators rewrite. Calling `M` "a graph" is not a
metaphor here — it is the denotation used by composition (§4.7) and
retrieval centrality (§4.8).

---

## 2. Predicate registry Σ and normalization

Natural language is not canonical: `owns`, `possesses`, `has`, `is owner of`
are one relation written four ways. Left alone they become four predicates,
no conflict is ever detected, and the algebra fragments. The registry fixes a
finite canonical alphabet

```
Σ = { P₁, …, P_k }
```

and normalization is the map from surface language into it

```
N_Σ : L → Σ            (L = surface predicate strings)
```

implemented in two layers: a total default form (casefold, trim, collapse
whitespace/hyphens to `_`) composed with an explicit alias table. `N_Σ` is
**idempotent**: `N_Σ(N_Σ(p)) = N_Σ(p)`.

---

## 3. Valuation ν

```
ν : M → [0,1]
```

`ν` assigns confidence to each fact. It is **not** a probability measure — it
does not normalize over alternatives and no independence is assumed. It is a
**ranking valuation**: its only algebraic role is to impose a preorder on
facts, used as a tie-breaker in canonicalization (§4.2) and a term in the
retrieval score (§4.8).

---

## 4. Operators O

Following the discipline of algebra, each operator is specified **by its
properties first**, then by its algorithm.

### 4.1 Normalize — `N : M → M`

*Properties.* Idempotent: `N(N(M)) = N(M)`. Predicate-local: it changes only
`p`, never `e`, `v`, `t`, `c`, or fact identity.

*Algorithm.* Replace each fact's predicate by `N_Σ(p)`. After `N`, aliased
facts share a conflict key and become visible to `C`.

### 4.2 Canonicalize — `C : M → M`

*Properties.*
* Idempotent: `C(C(M)) = C(M)`. *(test-backed, 100%)*
* Deterministic / order-invariant: `M = M′ ⇒ C(M) = C(M′)` as sets, regardless
  of iteration order. *(test-backed, 100%)*

*Definition.* Two facts **conflict** when they share `(e, p)` but differ in
`v`. `C` keeps one representative per conflict class:

```
C(M) =  ⋃   select(e, p)
      (e,p)∈keys(M)

select(e, p) = argmax over the class, under the TOTAL order
                 (1) higher timestamp   t
                 (2) higher confidence  c
                 (3) lower insertion index  seq        (final tie-break)
```

Because criterion (3) makes the order total, `select` is single-valued, which
is what forces determinism and idempotence.

### 4.3 Forget — `F : M → M`

*Properties.* Idempotent: `F(F(M)) = F(M)`. *(test-backed, 100%)* Contractive:
`F(M) ⊆ M`.

*Definition.* `F` removes facts failing a policy — expired `t`, confidence
below a floor, or (optional) contradiction pressure. `F` is a **projection**
onto the still-valid subset, not a rewrite toward a normal form (see §5 for
why this distinction matters).

### 4.4 Merge — `G : M × M → M`

*Properties.* On canonical states, `G` satisfies the **join-semilattice
laws**:

```
idempotent    G(M, M)          = M
commutative   G(M, N)          = G(N, M)
associative   G(G(M,N), K)     = G(M, G(N,K))
```

*(proved by argument in §6; also test-backed, 100% over 3000 random trials)*

*Definition.* `G(M, N) = C(M ∪ N)` (union deduplicates by fact id). This is
exactly a **Last-Write-Wins map**: see §6.

### 4.5 Promote — `Π-lift : Mᵢ → M₀`

Copies an episode fact into global memory `M₀` (a new fact, since facts are
immutable). This is the *only* cross-episode information flow; without it
episodes are isolated (§ episode partition below).

### 4.6 Project (query) — `P_q : M → M′`

`P_q(M) = { f ∈ M : q(f) }` for a predicate `q` over facts (by entity,
predicate, and/or value). A pure subset selection; `M′ ⊆ M`.

### 4.7 Compose — `comp : f × f → f`

Path composition on `G(M)`, valid when `f₁.v = f₂.e`:

```
(A —p→ B) ∘ (B —q→ C)  =  (A —p_q→ C)
```

The derived fact carries `ν(f₁)·ν(f₂)`, the newer timestamp, and provenance
to both parents. Composition is **partial** (defined only on adjacent edges).

### 4.8 Retrieve — `R`

A deterministic ranking, not similarity search:

```
R(M) = sort_desc  score(f)   over  C(F(M))

score(f) = α·ν(f) + β·recency(f) + γ·centrality(e)
```

Ties break on newer timestamp then insertion index, so `R` is a total,
reproducible order.

---

## Episode partition Π

```
M = M₀ ∪ M₁ ∪ … ∪ M_k ,     Mᵢ ∩ Mⱼ = ∅  (i ≠ j)
```

`M₀` is global; each `Mᵢ` is an episode. Writes are directed to the active
component; retrieval sees `M₀ ∪ M_active`. Cross-episode flow happens **only**
through `Π-lift` (§4.5), so episodes are non-interfering by default.

---

## 5. Reduction system and normal forms

Read `N`, `C`, `F` as reduction rules `M → M`. This is the rewrite-system /
abstract-reduction-system (ARS) lens, and it is the natural top-level view of
Dilmun. The relevant questions are termination, normal forms, and confluence.

**Termination.** `N` cannot increase the predicate-symbol count; `C` and `F`
cannot increase the fact count; all are bounded below. Every reduction
sequence terminates. *(proved by argument.)*

**Normal forms.**
* `M` is **canonical** when `C(M) = M`.
* `M` is **stable** when `F(M) = M`.

**Confluence — the earned result and its boundary.** We tested confluence
directly: run the reducers to a fixed point under every operator ordering and
compare the resulting states (3000 random states, `benchmarks/algebra_properties.py`).

```
core reduction system  {N, C}     → confluent in 100% of states
full reduction system  {N, C, F}  → confluent in  39.7% of states
```

So the honest statement is:

> The **normalizing core `{N, C}` is confluent**: normalization and
> canonicalization commute to a **unique canonical normal form**, independent
> of order. *(test-backed.)* This is the reduction-system property Dilmun has
> actually earned.
>
> **Forget does not join this confluence.** `F` and `C` do not commute,
> because the confidence floor (F) and the recency ranking (C) can disagree
> about which fact survives.

A concrete witness the harness found:

```
For a user with two 'city' facts —
    (user, city, X, t=high, c=0.2)      newest but low-confidence
    (user, city, Tampa, t=low, c=0.9)   older but confident

  C then F :  C keeps X (newest); F deletes X (c<0.5)  ⇒ city is FORGOTTEN
  F then C :  F deletes X (c<0.5); C keeps Tampa       ⇒ city = Tampa
```

Two valid orders, two different memories. `F` is therefore modeled as a
**policy projection applied at a fixed point in a chosen evaluation
strategy**, not as a confluent rewrite rule. Dilmun fixes that strategy: the
retrieval pipeline (§4.8) always evaluates `C ∘ F` in one order, so the
*result* is deterministic even though the *rule set* is not confluent.

### 5.1 Why the obstruction is structural (not about confidence)

It is tempting to "fix" `F` so the whole system becomes confluent. The
obstruction is deeper than the confidence policy:

> **Claim.** For any selection operator `C` (keep one representative per class)
> and any filter `F` that can remove `C`'s chosen representative, `C` and `F`
> do not commute.
>
> *Argument.* Take a class with a top-ranked fact `w` that fails the filter and
> a lower-ranked fact `u` that passes. `C∘F` filters first (`w` gone), so `C`
> selects `u`. `F∘C` selects first (`w` chosen), then filters `w` away, leaving
> the class empty. `u ≠ ∅`. ∎

So no redefinition of `F` *alone* buys commutativity: as long as `C` discards
non-winners before `F` can promote them, the two disagree. We confirmed this
empirically — a confidence-aware `F_ranked` moved full confluence only from
**40% to 49%**, nowhere near 100% (`benchmarks/forget_variants.py`).

### 5.2 The reducer is the composite `K = C ∘ F` (idempotent projection)

The right object is not two commuting rewrites but their **composite**, applied
in fixed order:

```
K = C ∘ F        "filter, then canonicalize"
```

> **Proposition.** `K` is idempotent: `K(K(M)) = K(M)`.
>
> *Argument.* `F(M)` contains only policy-passing facts. `C(F(M))` selects the
> per-class maximum among them, which is still policy-passing, so a second `F`
> removes nothing: `F(C(F(M))) = C(F(M))`. Then `C` is idempotent, so
> `C(F(C(F(M)))) = C(F(M))`. Hence `K∘K = K`. ∎  *(also test-backed, 100%.)*

`K` is therefore a well-defined **projection onto clean-canonical states**.
Fixing the evaluation order is not a workaround around a missing theorem — it
*is* the semantics, the same way a language pipeline (§ the retrieval order
`N → C → F → compose → R`) defines meaning by a fixed reduction strategy.

### 5.3 Research branch: should `F` become confidence-aware? (No.)

Evaluated on both axes (`benchmarks/forget_variants.py`, 3000 states):

| Forget variant | Full `{N,C,F}` confluence | `K=C∘F` idempotent | Matches intended semantics |
|---|---:|---:|---:|
| `F_global` (current) | 40% | 100% | **100%** |
| `F_ranked` (confidence-aware, keep-a-fallback) | 49% | 100% | **1.9%** |

`F_ranked` does **not** restore confluence (49% ≪ 100%, per §5.1) and it
*destroys* semantic quality: its fallback rule retains exactly the
low-confidence stale facts the floor is meant to discard, so it matches the
intended "trust, then take the latest" behavior only 1.9% of the time.
**Verdict:** keep `F_global` as the default. The confidence-aware variant
trades away memory behavior for an algebraic property it does not even achieve.
This is recorded as a closed research branch, not an open lever.

---

## 6. The merge substructure is a CRDT

The one place a classical structure emerges cleanly is merge. Per key
`(e, p)`, `C` keeps the fact maximal under the total order
`t > c > seq` — this is precisely a **Last-Write-Wins Register**. A whole
state is a map from `(e, p)` to such registers, i.e. an **LWW-Map**, a
standard state-based CRDT (CvRDT), and `G = C(· ∪ ·)` is its pointwise
**join**. The semilattice laws in §4.4 are exactly the CvRDT convergence
laws.

**Proof of the semilattice laws (by argument).** Per key `(e, p)`, `C` is
`max` under the total order `t > c > seq`, and set union `∪` is commutative,
associative, and idempotent. The laws follow because `C` distributes over
union as a max:

* *Commutative.* `M ∪ N = N ∪ M`, and `C` is a function of the set, so
  `G(M,N) = C(M∪N) = C(N∪M) = G(N,M)`. (Union dedupes by id; a shared id
  denotes the same immutable fact, so which copy is kept is immaterial.)
* *Associative.* For any key, `max` over a union equals the max of the
  submaxes: `max(max(A), K) = max(A ∪ K)`. Applying per key,
  `C(C(M∪N) ∪ K) = C(M ∪ N ∪ K) = C(M ∪ C(N∪K))`, i.e.
  `G(G(M,N),K) = G(M,G(N,K))`.
* *Idempotent.* `G(M,M) = C(M∪M) = C(M)`, which equals `M` when `M` is
  canonical.

The randomized tests (100%) are kept as regression checks on top of the proof,
per the "prove *and* fuzz" discipline. ∎

### 6.1 From single-store to multi-replica (implemented)

Two gaps stood between the single-store merge and a genuine multi-replica
CvRDT. Both are now closed in `dilmun/crdt.py` (opt-in; the default store is
unchanged).

* **Replica-consistent tie-break.** The single-store final tie-break is `seq`,
  a per-store insertion index — not consistent across replicas. The CRDT layer
  instead orders entries by `(timestamp, confidence, id)`, and `id` is a uuid
  that travels with the fact, identical on every replica. So all replicas pick
  the same winner regardless of local delivery order.
* **CRDT-safe removal.** Deletions are **tombstones**: a timestamped delete
  that participates in merges. A key is live iff its winning entry is a put, so
  a delete that dominates in time is not resurrected by merging with a replica
  that still holds the fact; a *newer* put after a delete correctly re-adds it.

> **Convergence.** Replicas that have absorbed the same set of operations reach
> identical state under any delivery order and any merge topology.
>
> *Argument.* Each replica's state is, per key, the `max` entry over the ops it
> has absorbed, under the global total order `(timestamp, confidence, id)`.
> `max` is order- and grouping-independent, so any two replicas that have seen
> the same op set compute the same per-key maximum. ∎  *(test-backed: 6
> replicas converge in 100% of 400 randomized trials,
> `benchmarks/crdt_convergence.py`.)*

The measurement also shows why the global tie-break is necessary: a naive
replica that keeps `seq`-style "first-delivered wins" on a timestamp tie
converges in only **75.5%** of the same trials — a quarter of them diverge.

*What is still open.* This is the CvRDT *state and merge*, not a network: there
is no transport, anti-entropy schedule, or vector-clock causality tracking
yet. Tombstones also accumulate (no garbage collection). And, as everywhere in
this document, convergence is test-backed, not machine-checked.

---

## 7. Fundamental properties — status table

| Property | Statement | Status |
|---|---|---|
| Immutability | facts are never mutated, only appended | by construction |
| Termination | every reduction sequence halts | proved by argument (§5) |
| Merge convergence | `G` obeys the semilattice / CvRDT laws | **proved by argument (§6)** + test-backed (100%) |
| Replica convergence | replicas with the same op set reach identical state | **proved by argument (§6.1)** + test-backed (100%, 6 replicas) |
| Reducer idempotence | `K = C∘F` satisfies `K(K(M)) = K(M)` | **proved by argument (§5.2)** + test-backed (100%) |
| Selection/filter non-commutation | `C` and `F` cannot commute | proved by argument (§5.1) |
| Referential stability | each canonical predicate = one identifier in Σ | by construction |
| Determinism | identical states ⇒ identical outputs | test-backed (100%) |
| Idempotence | `N`, `C`, `F` each satisfy `O(O(M)) = O(M)` | test-backed (100%) |
| Core confluence | `{N, C}` reach a unique normal form | test-backed (100%) |
| Full confluence | `{N, C, F}` reach a unique normal form | **fails (~40%)** by design — see §5 |

Rows are ordered by strength of guarantee: **proved by argument** (a written
proof above), then **test-backed** (checked empirically over randomized
inputs, *not* machine-checked), then the one deliberate **non-property**.
Promoting the test-backed rows to machine-checked proofs is the "formal
verification" roadmap item.

---

## 8. Mathematical inspiration (not foundation)

Dilmun's design borrows a *philosophy*, not a theorem, from ring theory —
specifically from Wedderburn's little theorem (every finite division ring is
commutative), and the exposition in Kaczynski's 1964 note "Another Proof of
Wedderburn's Theorem."

The lesson worth borrowing is Wedderburn's shape of argument: **a structure
that looks maximally free turns out to be rigid** — finiteness alone forces a
non-commutative object to commute. Dilmun aims at the analogous move for
memory: messy, redundant, contradictory input is forced, by immutability plus
deterministic reduction, into a rigid canonical form; and operations that look
order-dependent (merge) turn out to be order-independent.

That is the whole of the connection, and it is an **analogy**. Dilmun's
objects are labeled graphs, partial orders, and rewrite operators — not
division rings. We do **not** claim Wedderburn's theorem as a foundation,
mechanism, or correctness argument. Invoking it that way would be borrowing
prestige; the algebra above is meant to stand on its own definitions.

---

## 9. What we do not claim

* Not a ring, semiring, or field — no distributive pair of operations is
  defined over `M`.
* Not a general lattice — only `merge` is shown to be a semilattice join;
  no meet is defined.
* Not a category — no composition/identity laws are established over states.
* Not confluent as a whole — see §5.
* Not machine-verified — all "test-backed" claims are empirical.

These are invitations, not apologies: each is a place where the theory could
be developed if the structure genuinely emerges.
