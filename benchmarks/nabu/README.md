# bench_nabu — the scribe-of-the-world benchmark

Named for **Nabu**, the Babylonian god of scribes and record-keeping. An agent
runs missions to **amass verified facts** across three domains that triangulate
human physical experience:

- **body** — emergency medicine (WHO essential drugs; openFDA labeling)
- **matter** — chemistry (PubChem; public domain)
- **culture** — anthropology (the D-PLACE / Ethnographic Atlas record)

Every target fact is checkable against an authoritative snapshot, so the
benchmark **never grades an LLM with an LLM** — it grades against PubChem, the
drug record, and the ethnographic record.

## Why these three

They *link*. A drug's active moiety **is** a chemical compound; that compound
has a molecular formula. So `compose()` derives **body ↔ matter** facts no
single source wrote (`med:epinephrine ∘ epinephrine ⇒ C9H13NO3`). Culture is
the third axis — breadth, not a numeric bridge. Together they cover a lot of
what a human being can physically undergo, which is the point.

## The efficiency thesis (how to amass knowledge cheaply)

1. **Structured sources first.** All three domains expose facts pre-shaped as
   triples (PubChem PUG REST, openFDA, D-PLACE CSVs). The agent's job shrinks
   from *extraction* to *navigation* — facts-per-token jumps, and every write
   stays checkable.
2. **The frontier is the curriculum.** Seed a small manifest, then let
   composition grow the reading list: any fact whose value is a **new** entity
   (a drug's active_moiety → a compound) becomes the next mission target. BFS
   over the knowledge graph.
3. **Verify-then-trust ν.** API facts enter at high confidence; prose facts
   low until a second source agrees. Disagreement → contradiction → the
   veridicality guard abstains. Quality is a *policy*, not a hope.

## Run

```sh
py benchmarks/nabu/bench_nabu.py --baseline            # deterministic floor + snapshot (offline)
py benchmarks/nabu/bench_nabu.py --baseline --refresh  # + cross-check chem seed vs live PubChem
py benchmarks/nabu/bench_nabu.py --agent store.json --tokens 42000
```

`--baseline` fills the manifest directly (coverage 1.0, veridicality 1.0 by
construction). It is both the **floor** an agent must beat and the writer of
`ground_truth.json`, after which all scoring is fully offline and reproducible.

## Metrics (all deterministic, computed through the real operators)

| metric | question |
|---|---|
| `coverage` | filled (entity, predicate) / manifest |
| `veridicality` | strict facts whose value matches the authority (numeric tol for MW) |
| `confabulation_rate` | canonical writes on a known key with a **wrong** value |
| `off_schema_rate` | canonical writes on entities/predicates never asked for |
| `duplicate_suppression` | canonical / raw — is `canonicalize()` earning its keep |
| `cross_domain_yield` | `derive()` facts whose parents span two domains |
| `efficiency` | canonical facts per 1k tokens (agent) or facts/sec (baseline) |
| `temporal_grounding` | `timer_stop − timer_start` — duration as a fact-difference |

## Pi mission contract

A Pi mission produces the `store.json` this benchmark scores. Register a
`dilmun_write_fact` tool in the Dilmun Pi-extension; the mission calls it for
every fact it accepts. Export the resulting store as:

```json
{ "facts": [
  { "entity": "epinephrine", "predicate": "molecular_formula",
    "value": "C9H13NO3", "timestamp": 1720800000, "confidence": 0.98 },
  { "entity": "med:epinephrine", "predicate": "active_moiety",
    "value": "epinephrine", "timestamp": 1720800001, "confidence": 0.95 }
] }
```

Entity id conventions (so the cross-domain bridge composes):
`chem` = bare compound name (`epinephrine`), `med:` and `soc:` prefixed. A
drug's `active_moiety` value must equal the compound's entity id.

Give the mission a **timer**: write `session.timer_start` at launch and
`session.timer_stop` at settle, so the run earns a scored duration.

## Honesty labels (printed in every run header)

- **chem** — PubChem is authoritative; `molecular_formula` and
  `molecular_weight` are strictly checked, `cid` is recall-only.
- **med** — reflects standard EM practice and US-approved labeling; the medical
  record, not universal or individualized medical truth.
- **anthro** — the ethnographic record carries known Murdock-era sampling and
  coding biases; this scores **recall of that record**, not truth about living
  cultures.

## Files

- `nabu_seed.json` — versioned manifest + hand-checked authoritative values.
- `bench_nabu.py` — sources, baseline harvester, scorer, CLI.
- `ground_truth.json` — snapshot written by `--baseline` (offline scoring).
- `sample_agent_store.json` — an intentionally imperfect fixture (missing
  societies, a wrong caffeine MW, duplicate re-ingests, a mission timer).
