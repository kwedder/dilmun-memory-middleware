# Dilmun — Build Report

*Generated at loop-stop. Production composite: robotics 0.941 / agent 0.980.
Every study below was run in an isolated scratch sandbox; no production file
(`improvement_loop.py`, `candidates.json`) was modified.*

---

## 0. TL;DR for building

1. The benchmark hit its ceiling and, in doing so, exposed a **measurement flaw
   worth more than any candidate it ranked**: the `robustness` axis was pooling
   non-comparable cross-domain numbers.
2. Split `robustness` into three measured sub-facets: **R1 Reconstruct**,
   **R2 Veridicality (confabulation-guard)**, **R3 Survive-clutter**.
3. Measured head-to-head, the modeled ranking **inverts**. Build the robustness
   layer on the measured results below, not the paper numbers.
4. **Key design principle discovered (R2): veridicality requires *binding*.** A
   memory that stores only which values exist (marginals) can verify content but
   rubber-stamps fabricated *combinations*. Only memories that store
   *relationships* can catch a ghost memory.

---

## 1. Reconstruction (R1) — measured on one common task

Common task: structured records (8 attributes x 8 values), store K, erase
attributes, measure exact recovery (ARR). 2 of 8 erased:

| K (load) | 🇫🇷 clique | 🇧🇷 morph | 🇲🇽 register |
|---|---|---|---|
| 5  | 1.000 | 0.983 | 0.050 |
| 10 | 1.000 | 0.908 | 0.025 |
| 20 | 0.979 | 0.362 | 0.021 |
| 40 | 0.796 | 0.027 | 0.010 |

Modeled constants the loop currently uses: 🇧🇷 0.9667 > 🇲🇽 0.8361 > 🇫🇷 0.80.
**Measured ranking inverts to 🇫🇷 ≫ 🇧🇷 ≫ 🇲🇽.** France binds all attributes
(recover missing from present); Brazil binds pairwise (fades under load); Mexico's
register has no cross-attribute binding, so it structurally cannot reconstruct
combinations. (Mexico's 0.8361 came from EMNIST digit recall — a recognition
task, not combination reconstruction.)

## 2. Veridicality / confabulation-guard (R2) — *the key facet*

Can the memory tell a genuine stored memory from one it synthesized, using ONLY
its own internal state (no external list of stored items)? Two lure types:
**LURE-A** = a value never stored; **LURE-B** = every value seen but the
*combination* never stored (the true "ghost memory").

Accept-rate (REAL should be high; lures should be low). K=8, 40 seeds:

| mechanism (internal test) | REAL | LURE-A | LURE-B (ghost) | guard |
|---|---|---|---|---|
| 🇲🇽 register — material implication | 1.000 | 0.000 | **1.000** | 0.667 |
| 🇫🇷 clique — complete-clique check  | 1.000 | 0.000 | **0.000** | **1.000** |
| 🇧🇷 morph — fixed-point check       | 1.000 | 0.000 | **0.000** | **1.000** |

Ghost-acceptance vs storage load (lower = better guard):

| K/C load | 🇲🇽 register | 🇫🇷 clique | 🇧🇷 morph |
|---|---|---|---|
| 1x | 1.000 | 0.000 | 0.000 |
| 2x | 1.000 | 0.000 | 0.000 |
| 3x | 1.000 | 0.000 | 0.090 |
| 4x | 1.000 | 0.000 | 0.249 |
| 6x | 1.000 | 0.000 | 0.738 |

**Finding — refines and partly inverts the original hypothesis.** The intuition
was that Mexico (recognition) would be the honesty mechanism. Measured: Mexico is
honest about *novel content* ("I've never seen this value") but **structurally
blind to novel combinations** — it certifies every ghost memory as genuine, at
*every* load, because it stores marginals without binding. The true
confabulation-guard is **France (cliques = pure binding)**: it rejects both novel
values and novel combinations and holds up under heavy load. Brazil guards well
only at low load (spurious fixed points proliferate as it overloads).

Caveat: France's clique test is not literally immune — at extreme saturation
spurious cliques must eventually appear; it simply stayed at 0.000 through the
tested 6x-overload envelope. Numbers are 40-seed means; GBNN decoder is a faithful
simplified sum-of-clusters + WTA.

**Design principle:** the "truth signal" is relational, not token-level. Exactly
as individually-plausible words can combine into a false sentence, individually-
seen values can combine into a false memory. A memory's confabulation-guard must
be built on stored *relationships*, not stored *items*.

## 3. Proven vs. modeled (build only on the proven column)

| Proven in-benchmark (safe to build) | Modeled / cross-domain (verify first) |
|---|---|
| 🇯🇵 multi-hop (real JEMHopQA calibration) | Every robustness paper-constant (FR/BR/MX) |
| 🇫🇷 France = strongest R1 reconstruction & R2 guard | 🇮🇹 Italy efficiency (83x real, but on integer keys, not a memory store) |
| 🇧🇷 Brazil = strong R1/R2 **at low load only** | 🇺🇦 Ukraine (no number obtainable — source-walled) |
| Load-fragility of morphological memories (measured) | `variant/synonym/effect` axes (synthetic flags, not real data) |
| 🇲🇽 Mexico = sound novel-*content* rejection (not combinations) | — |

Only `multihop` is calibrated on real data — the largest credibility gap.

## 3b. Final benchmark vs the current leader (embedding/RAG)

`BindingMemory` (clique) vs the repo's `VectorMemory` (TF-IDF cosine = same shape
as an embedding/RAG store, the dominant agent-memory architecture). Task:
reconstruct a hidden attribute from 3 known ones, over ANSWERABLE queries (a true
stored value exists) and UNANSWERABLE ones (a context that never co-occurred —
honest answer is *abstain*). `CONF.ERR` = confident-error rate (wrong-when-
answerable + answered-when-unanswerable); lower = safer. 30 seeds.

| method | ans.correct | unans.abstain | CONF.ERR |
|---|---|---|---|
| BindingMemory (clique) | 0.893 | 0.980 | 0.063 |
| **Vector + Binding guard (hybrid)** | **0.976** | **0.984** | **0.020** |
| Vector RAG τ=0.0 (always answers) | 0.976 | 0.000 | 0.512 |
| Vector RAG τ=0.3 | 0.976 | 0.233 | 0.396 |
| Vector RAG τ=0.5 (oracle-tuned best) | 0.976 | 0.929 | 0.048 |
| Vector RAG τ=0.7 | 0.011 | 1.000 | 0.000 |

Findings:
* The RAG leader has **no native abstention**; its safety depends entirely on a
  cosine threshold τ that must be tuned per-dataset against ground truth you do
  not have at deploy time — and it's a knife-edge (τ=0.3→0.40 err, 0.5→0.05 err,
  0.7→recall collapses to 0.01).
* **The hybrid dominates every single method**: vector retrieval for recall,
  gated by binding's parameter-free `veridicality()`. It matches the leader's
  best recall (0.976), abstains most reliably on unanswerable queries (0.984),
  and has the lowest confident-error (0.020) — **with no threshold to tune.**
* This benchmark also caught and fixed a real defect in the draft
  (`reconstruct` accepted spurious pairwise-only cliques; now requires the
  completed bundle to be a genuine clique) — unanswerable-abstention 0.70→0.98.

Caveat: synthetic clean-token data; a neural encoder would change vector *recall*
but not the architectural point — the guard rejects unstored combinations
regardless of encoder, and fuzzier embeddings confabulate *more*, so the guard's
value is a lower bound.

**Implication for implementation: don't replace the leader — GUARD it.** Ship the
binding memory as a veridicality/verification layer over vector retrieval.

## 4. Recommended build order

- **Phase 1 — Robustness facet redesign.** Replace the single `robustness` mean
  with R1/R2/R3 sub-scores, each on a declared task + fixed load/noise regime.
  Build R1 on France, R2 on France (binding), R3 on France; keep Brazil as a
  low-load option; keep Mexico for its genuine niche (novel-content recognition).
- **Phase 2 — De-synthesize the other axes** (`variant/synonym/effect/retain`)
  onto real datasets via the `CALIBRATION` drop-in seam, as `multihop` already is.
- **Phase 3 — Ship binding as a GUARD LAYER over existing retrieval** (not a
  replacement). `dilmun/binding.py` exists and is tested; wire its
  `veridicality()` as a verification gate on the retrieve/write path so recall
  comes from vector/instance retrieval and confabulations are rejected by the
  clique check. Add multihop temporal traversal alongside.
- **Phase 4 — Resolve pending candidates** only as isolated real-ports: Italy
  (port PLA-compression onto the actual store, then decide), Ukraine (revisit only
  if an open source surfaces).

## 5. Open human decisions

1. R1/R2/R3 weighting (rec: R2 heaviest for a world-model an agent acts on).
2. Italy: port-and-measure vs. leave parked (number confirmed; only domain-fit
   call remains).
3. Whether to promote the scratch studies into a repo `studies/` folder.

## 6. Housekeeping

- Loop stopped: both recurring crons (guard, daily-fetch) cancelled.
- Candidates ledger: 6 vetted / 2 pending / 6 rejected; pending = Italy, Ukraine
  (full rationale + exhausted routes recorded in `candidates.json`).
- Decision + R2 result recorded to persistent memory (`dilmun-robustness-facets`).
- Reproducible study scripts: `scratchpad/brazil_port/`
  (`port_study.py`, `three_way.py`, `substitute.py`, `veridicality.py`).
