# Dilmun for Robotics — Research Findings & Improvement Directions

*A data-backed scan of memory-system research (uncovered technostates) for ways
to improve Dilmun on robots. Deployment context: a local open-source AI harness
driving a set of **ESP32-based robots** — chosen for budget, with the intent that
the same memory layer scales up to more complex robots later. So the design goal
is **bounded, not limited**: fit in hundreds of KB and no GPU, without being
architecturally capped there.*

Honesty note (house rule): each lead below carries a real, fetched citation.
Where a number couldn't be verified from an accessible source, it's flagged. The
research loop that produced this is the same data-only pipeline used for the
benchmark candidates — no invented papers or figures.

---

## Summary — four improvement directions

| # | Direction | Source (nation) | Dilmun module it extends | On-device fit |
|---|---|---|---|---|
| 1 | Episodic→semantic **consolidation** | 🇳🇱 Netherlands | `Fact` + `forget` (new operator) | ✅ shrinks the store |
| 2 | Cross-robot **compiled-digest transfer** | 🇷🇴 Romania (inferred) | `crdt.py` / `merge_all` | ✅ deterministic, no GPU |
| 3 | Static / **bounded-memory discipline** | ⚙️ embedded (STM32, Cortex-M4) | store internals, ESP32 port | ✅ predictable RAM/WCET |
| 4 | **Confabulation guard** (already built) | (this project) | `guard.py` | ✅ rejects noisy-sensor ghosts |

---

## 1. Episodic → semantic consolidation  🇳🇱 (highest value)

**Source:** Kim, Cochez, François-Lavet, Neerincx, Vossen — *A Machine With
Human-Like Memory Systems*, TU Delft / VU Amsterdam.
https://arxiv.org/abs/2204.01611

**What they do.** Memory is RDF-like triples split into two stores:
- **episodic** — `(head, relation, tail, timestamp)`, e.g. `(James's_laptop, AtLocation, desk, 42)`
- **semantic** — `(head, relation, tail, strength)`, e.g. `(laptop, AtLocation, desk, 10)`
where *strength = how often the regularity was seen*. Repeated specific episodes
**consolidate** into a general semantic fact (drop the instance, accumulate
frequency); when episodic memory is full, similar episodes are compressed/forgotten.
An agent with **both** stores generalizes better as capacity grows.

**Why it fits Dilmun.** This is almost exactly Dilmun's `(e, p, v, t, ν)` model —
episodic ≈ a timestamped fact, semantic ≈ a strength-weighted generalization. The
missing piece is the **consolidation operator**: fold N repeated observations of
`(entity, predicate, value)` into one semantic fact whose confidence rises with
repeated confirmation, and reclaim the episodic instances. For a robot this is
*compression and generalization at once*: "seen the charger at dock 20 times" → one
strong semantic fact, 19 facts freed.

**Robotics payoff.** Directly attacks the on-device RAM budget while making the
robot smarter (it learns regularities). Deterministic and additive.

*Caveat: their evaluation is comparative graphs in a gridworld ("the Room"), not
an exact numeric delta; their store/forget policies are hand-crafted (they name RL
policies as future work).*

→ **Drafted as a module this session: `dilmun/consolidate.py` (see below).**

## 2. Cross-robot compiled-digest transfer  🇷🇴 (high value for a fleet)

**Source:** Abaza, Staicu, Doicin — *A Semantic Autonomy Framework for
VLM-Integrated Indoor Mobile Robots: Hybrid Deterministic Reasoning and
Cross-Robot Adaptive Memory*. https://arxiv.org/abs/2605.02525
*(author names indicate Politehnica Bucharest, Romania — affiliation inferred, not
confirmed on the fetched page).*

**What they do.** A **7-step deterministic resolver handles 88% of instructions in
< 0.1 ms** with no LLM/camera/GPU. Preferences learned via the VLM on one robot are
"promoted to deterministic resolution and transferred to a second robot via a
**shared compiled digest**" → reported **103,000× latency reduction** and **100%
semantic transfer accuracy (33/33, 95% CI [0.894, 1.000])**. Memory is symbolic,
organized by scope (global environment / per-operator / per-robot).

**Why it fits Dilmun.** You're deploying a *set* of robots, and Dilmun already has
a CRDT layer (`merge_all`, `LWWMap`) for conflict-free merge. This adds the missing
idea: **compile stable/high-strength facts into a compact digest and propagate it
across the fleet**, so robot #2 instantly inherits robot #1's learned regularities
and most decisions skip the expensive model path. The scope taxonomy (global vs
per-robot vs per-operator) maps naturally onto Dilmun episodes/partitions.

**Robotics payoff.** Fleet-wide learning + a deterministic fast path that avoids
the LLM for the common case — ideal for cheap, intermittent-connectivity robots.

## 3. Static / bounded-memory discipline  ⚙️ (implementation guidance)

**Sources:**
- *Deterministic Static-Memory Architecture* (RRT planner on **STM32**) — fits
  complex geometric planning within a **20 KB SRAM** constraint by eliminating
  dynamic allocation, enabling static verification + WCET analysis.
  https://www.researchsquare.com/article/rs-8473610/v1.pdf *(403 on fetch; 20 KB
  figure from the abstract snippet, not personally verified).*
- *NavHD: Low-Power Learning for Micro-Robotic Controls* (Stanford) — navigation
  inference on a **Cortex-M4 in 10.2 KB, 900 cycles/inference, 1.1 mJ/frame**.
  https://web.stanford.edu/~chae/paper/navhd.pdf

**Why it matters.** Not a new algorithm — a constraint for the ESP32 port. To be
"bounded, not limited," Dilmun's store should offer a **statically-sized profile**:
a fixed fact budget, ring-buffer episodes, bounded dictionaries, and no unbounded
growth — so worst-case RAM and timing are predictable (WCET-friendly). The
consolidation operator (#1) is the mechanism that keeps the store *under* budget;
this direction is about making the data structures themselves bounded. On a richer
robot the same code runs with a larger budget — the ceiling is a config, not a
rewrite.

## 4. Confabulation guard (built this session)

`dilmun/guard.py` — the veridicality guard is itself a robotics feature: sensors
are noisy, and a memory that confidently "recalls" a combination it never actually
observed is dangerous for an agent that acts on it. The guard rejects ghost
memories deterministically, with no GPU. Already implemented and tested.

---

## Recommended sequence

1. **Consolidation operator (#1)** — biggest single win; solves the RAM budget and
   adds generalization. *(Draft landed this session.)*
2. **Bounded-store profile (#3)** — make the structures statically sized so the
   ESP32 target is provably in-budget; same code scales up by config.
3. **Fleet digest transfer (#2)** — layer onto the existing CRDT sync for
   multi-robot learning once single-robot memory is solid.

## Nations status

New this pass: 🇳🇱 Netherlands (consolidation), 🇷🇴 Romania (cross-robot, inferred).
Embedded references (STM32 paper nation unconfirmed; NavHD = US/Stanford) are cited
as implementation guidance, not nation-scored candidates. Previously covered
nations were excluded per the research-loop protocol.
