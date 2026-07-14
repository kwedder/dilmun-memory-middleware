# bench_swarm — scale + multiple runners (design spec)

Extends `bench_nabu` along two axes at once: **volume** (hundreds→thousands of
verified facts) and **concurrency** (K runners collecting into their own Dilmun
replicas, then merging). Same operators, same vetted-source rule, same
deterministic scoring against an authoritative snapshot.

This is the CRDT/merge core under load, and — swap "collect a PubChem fact" for
"sense a reading at grid D6" — it's the drone-swarm benchmark in disguise.

## The payoff

Give runner A the drugs and runner B the compounds. Neither can answer
"epinephrine's formula" alone. After `merge()`, `compose` bridges the slices and
derives it — a fact **no single runner could produce**. Measured as
`cross_runner_yield`.

## Setup

1. **Ground truth at scale** — `--harvest --scale N` pulls N real entities from
   the vetted APIs (PubChem compounds, openFDA/WHO drugs, D-PLACE societies) and
   freezes `ground_truth.json`. All later runs score offline against it.
2. **Partition** — split the manifest across K runners by `hash(entity) % K`,
   with tunable `--overlap` so slices intersect (forces cross-runner dedup +
   conflict). Each runner emits `store_k.json` (same shape a Pi mission emits).
3. **Merge & score** — `operators.merge` (HLC tie-break + LWW-Map from
   `crdt.py`) folds the K stores into one; the existing scorer runs plus the
   swarm metrics below.

```sh
python3 benchmarks/nabu/bench_swarm.py --harvest --scale 500
python3 benchmarks/nabu/bench_swarm.py --runners 8 --overlap 0.3
```

## The four runs

| run | what it isolates |
|---|---|
| **SOLO×N** | one runner, big manifest — scaling curve; proves volume alone doesn't degrade quality |
| **K DISJOINT** | K runners, non-overlapping slices — parallel throughput + the compose payoff |
| **K OVERLAP** | K runners, overlapping slices — dedup-across-runners + guard tie-break at scale |
| **+1 BAD** | K good + 1 adversarial runner (unvetted / wrong values) — containment |

## New metrics (on top of bench_nabu's)

| metric | asks | healthy |
|---|---|---|
| `convergence` | all K replicas reach an identical canonical state post-merge? | 1.000 |
| `merge_order_independence` | merge in shuffled orders → same result? | 1.000 |
| `dedup_across_runners` | unique canonical / total raw writes across runners | ≈ manifest size |
| `cross_runner_yield` | ∘ facts whose parents came from different runners | > 0 |
| `containment` | with 1 bad runner, veridicality/vetted-rate stay bounded, junk flagged | guard holds |
| `scaling` | coverage · veridicality · merge-cost · facts/sec vs N, K | flat quality, sane cost |

`convergence` is the one that matters most: if K drone-runners on a flaky link
don't provably reach the same memory, nothing else counts. The CRDT benches
already show 1.000 on synthetic ops — this proves it on **real acquired facts at
volume**.

## What failure would teach

- non-convergence → a tie-break that isn't total (fix the HLC/LWW ordering)
- dedup blow-up → entity-keying too brittle for independent collectors
- poisoned merge → the guard needs a per-source trust weight

Each failure names the next fix, the way bench_nabu's confluence-0.397 gap did.

## Honesty carried forward

Anthropology stays labeled as recall of a biased record; the large snapshot
inherits whatever the source APIs got wrong (scored as fidelity-to-source, not
truth); "runners" are processes, not yet drones — merge semantics are identical,
on-hardware timing/partition is future work.

## Build notes

Reuses: `operators.merge`, `crdt.py` (LWW-Map + HLC), `nabu_seed.json` /
`vetted_sources.json` / the scorer in `bench_nabu.py`. New file
`bench_swarm.py` adds harvest-at-scale, partitioning, K-way merge, and the swarm
metrics. Report: shared as a claude.ai artifact (bench design).
