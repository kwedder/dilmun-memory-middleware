# Candidate techniques — data-only intake for the improvement loop

`improvement_loop.py` auto-loads every entry in `candidates.json` whose
`status == "vetted"` and scores it alongside the 11 built-in techniques. This
is the "seamless acceptance" path: vet a candidate → flip it to `vetted` → the
running guard (`--guard`, cron `cbe1d252`) picks it up on its next fire and
reports the SHIFT.

## Hard rule: DATA ONLY, no guesses

A candidate is admissible **only** if every field below is backed by a real,
checkable source. If a source or measured number cannot be produced, the
candidate is dropped — not softened, not estimated. No invented papers, no
"likely," no round-number placeholders.

## Schema (one object per candidate in `candidates.json`)

```json
{
  "key": "KR",                       // 2–3 char unique code, not already in use
  "name": "🇰🇷 memory-augmented net", // flag + ≤3-word label
  "nation": "South Korea",
  "technique": "one-line description of the memory mechanism",
  "axis": "multihop",                // EXACTLY one of the loop's axes (below)
  "on": 0.90,                        // in [0,1]: the axis score the technique
                                     //   achieves, taken from the cited metric
  "footprint_delta": 1.0,            // efficiency axis only: multiplicative
                                     //   footprint factor (<1 = smaller store)
  "citation": "https://arxiv.org/abs/....",  // real, resolvable URL
  "benchmark": "KLUE-MRC",           // named native/nation benchmark
  "metric": "EM 90.4 on KLUE-MRC (Table 3)", // the exact measured number+where
  "maps_to": "compose/derive",       // which Dilmun slot it extends (additive)
  "status": "pending"                // reviewer flips to "vetted"
}
```

## Axes (a candidate must map to exactly one)

`multihop · crossling · variant · synonym · effect · retain · efficiency · robustness`

- accuracy axes (`multihop…retain`): `on` lifts that axis toward the cited score.
- `efficiency`: set `footprint_delta` (<1 shrinks the store); `on` ignored.
- `robustness`: `on` is folded into the robustness mean.

## Vetting checklist (before flipping to `vetted`)

1. `citation` resolves and the `metric` number actually appears there.
2. `benchmark` is a real, named evaluation (not invented).
3. Technique is implementable as a **deterministic, additive** mechanism on one axis.
4. `nation` is not already covered (RU, ZH, JP, NO, IN, DE, TW, IL, AE, SG, Africa).
5. `key` is unique.

Anything failing a check stays `pending` (or is removed).
