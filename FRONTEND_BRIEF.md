# Dilmun Memory Console — Frontend Build Brief

*A complete, self-contained brief for an AI frontend agent. You can build the
entire UI against the mock data in §9 with no backend, then swap in the real API
(§6) later. Read §1–§3 for context, §4–§8 to build, §9 for seed data.*

---

## 1. What this product is

**Dilmun** is a deterministic memory system for AI agents. Instead of storing text
blobs and retrieving "the closest-looking thing" (how most RAG/vector memories
work), it stores structured **facts** and — critically — it can tell the
difference between a **genuine stored memory** and a **confabulation** (something
that merely looks plausible). That honesty signal is the product's differentiator.

You are building the **Dilmun Memory Console**: a web UI for a developer or
researcher to *inspect, write, retrieve, and verify* an agent's memory. Think
"database console meets observability dashboard," with one unique twist — a
**Veridicality Guard** that visibly flags when a recalled memory is real vs.
made-up.

**Audience:** technical (AI engineers, researchers). **Tone:** clean, calm,
trustworthy, data-dense but not cluttered. Not consumer-flashy.

## 2. The one idea that makes this special

Most AI memory *always answers*, even when the honest answer is "I never learned
that" — that's how confident hallucinations happen. Dilmun can **abstain** and can
**score how genuine** a claim is. Your UI's job is to make that truth signal
**front and center and legible**, and to make *abstention feel like a feature,
not a failure*. If you nail one thing, make it the **Veridicality Guard** (§5.5).

## 3. Core concepts (domain glossary)

| Term | Meaning for the UI |
|---|---|
| **Fact** | The atomic unit: `(entity, predicate, value)` + metadata. E.g. entity `obj1`, predicate `color`, value `blue`. Read like a sentence: "obj1's color is blue." |
| **Entity** | The thing a fact is about (`user`, `obj1`, `paris`). |
| **Predicate** | The attribute/relation (`color`, `favorite_food`, `capital_of`). |
| **Value** | The attribute's value (`blue`, `pizza`). |
| **Confidence (ν)** | 0–1 certainty attached to a fact. |
| **Episode** | A named partition of memory (like a session/scope). Writes land in the open episode; retrieval sees global + active episode. |
| **Retrieval / Context** | The ranked set of facts the agent would recall, scored by confidence + recency + graph centrality. |
| **Veridicality** | 0–1 score for "is this claim a genuinely stored memory?" 1.0 = fully attested; lower = suspicious; 0.0 = never stored. |
| **Verdict** | Result of a check: `{ genuine: bool, veridicality: number, reason: string }`. The `reason` is human-readable — show it. |
| **Confabulation / ghost memory** | A claim whose parts were each seen, but **never together**. The guard rejects these. This is the headline capability. |
| **Reconstruct** | Fill in a missing attribute from known ones — or **abstain** (return null) rather than guess. |
| **Advisory mode** | The guard *watches and flags*; it never blocks or deletes. Reflect this: the UI warns, it doesn't hard-stop. |

## 4. Primary user stories

1. **Browse memory** — see all facts as a filterable table; filter by entity /
   predicate / episode.
2. **Write a fact** — a form to add `(entity, predicate, value, confidence)`.
3. **See what the agent would recall** — the ranked Context view with scores.
4. **Explore relationships** — a graph of entities → (predicate, value).
5. **★ Verify a claim (Veridicality Guard)** — enter a candidate memory; get a
   genuine/suspicious/fake verdict with a score meter and the reason.
6. **★ Reconstruct / ask** — provide some known attributes, ask the memory to
   fill a blank; clearly show when it **abstains**.
7. **Switch episodes** — open/close/select an episode partition.

★ = the differentiating screens; give them the most design love.

## 5. Screens & components

Use a persistent left nav (Facts · Context · Graph · **Verify** · **Reconstruct** ·
Episodes) + a top bar showing the active episode and a stats chip
(`N facts · M entities · K episodes`).

### 5.1 Facts (table)
- Columns: Entity, Predicate, Value, Confidence (as a small bar), Episode, Time.
- Filters: text search + dropdowns for entity/predicate/episode.
- Row click → detail drawer (all metadata incl. `id`, `seq`, `derived_from`).
- Primary action button: **+ Write fact** (opens the form, §5.2).
- States: loading skeleton, empty ("No facts yet — write your first"), error.

### 5.2 Write Fact (form / modal)
- Fields: Entity (text), Predicate (text, autocomplete from existing predicates),
  Value (text), Confidence (slider 0–1, default 1.0), Episode (select, default =
  active), TTL (optional).
- On submit → POST, optimistic insert into the table, toast confirmation.
- **Bonus honesty touch:** after submit, optionally show the new fact's
  veridicality against existing memory (is it consistent with what's known?).

### 5.3 Context (ranked recall)
- Same rows as Facts but **ordered by score** (descending) with a visible
  `score` value/bar per row. Optional `limit` control.
- Caption explaining the score = `0.5·confidence + 0.3·recency + 0.2·centrality`.

### 5.4 Graph
- Node-link diagram: entities as nodes, edges labeled by predicate pointing to
  value nodes. Click a node → its facts. Keep it legible; this is secondary.
- A simple force/DAG layout is fine; don't over-engineer.

### 5.5 ★ Verify (the Veridicality Guard) — the hero screen
Purpose: let the user assemble a candidate memory and see if it's real.

- **Input:** an entity (optional), a set of **known** `(predicate = value)` chips
  the user adds, plus a **claim** `(predicate = value)` to test.
- **Action:** "Check" → calls `/verify`.
- **Output — make this beautiful and unambiguous:**
  - A large **Veridicality Meter** (0–100%) — a radial or horizontal gauge.
  - A verdict badge with three semantic states:
    - `genuine` (score ≥ threshold, default 1.0) → **green** "Attested".
    - `0 < score < threshold` → **amber** "Unattested combination — possible confabulation".
    - `score = 0` → **red** "Never stored".
  - The **`reason` string** shown verbatim beneath the badge (it's written to be
    read by a human).
  - A short plain-language gloss you generate from the state, e.g. amber →
    "Every piece is real, but they were never seen together."
- **Preset examples** the user can click to see each state (use §9 seed data):
  a genuine bundle, a novel-value claim, and a ghost recombination. This teaches
  the feature instantly.

### 5.6 ★ Reconstruct / Ask
- **Input:** known `(predicate = value)` chips + one or more **target** predicates
  to fill.
- **Action:** "Reconstruct" → `/reconstruct`.
- **Output:** for each target, either the recovered value **or an explicit,
  positively-framed abstention**: a calm "Abstains — no confident answer" chip
  (NOT an error/red). Microcopy matters: this is the memory being honest, and the
  UI should celebrate it, e.g. a subtle "🛡️ chose not to guess" tag.

### 5.7 Episodes
- List episodes with opened/closed status + tags. Actions: Open, Close, Select
  (select drives the active-episode context everywhere).

## 6. Proposed API contract

The Python library already implements all of this logic; a thin HTTP wrapper
(FastAPI/Flask) can expose it. **Build against these JSON shapes.** Base path
`/api`. All responses JSON; errors → `{ "error": string, "message": string }`
with HTTP 400/404/500.

### Facts
```
GET  /api/facts?entity=&predicate=&episode=      -> Fact[]
POST /api/facts        body: WriteFact           -> Fact
GET  /api/context?limit=                         -> ScoredFact[]
GET  /api/graph                                  -> { [entity]: [ [predicate, value], ... ] }
GET  /api/stats                                  -> { facts, entities, episodes }
```

### Episodes
```
GET  /api/episodes                               -> { [id]: Episode }
POST /api/episodes/{id}/open                     -> { active: id }
POST /api/episodes/{id}/close                    -> { active: null }
```

### Veridicality (the guard)
```
POST /api/verify        body: VerifyReq          -> Verdict
POST /api/verify-fact   body: WriteFact          -> Verdict
POST /api/reconstruct   body: ReconstructReq     -> { [predicate]: value | null }
POST /api/guard         body: GuardReq           -> { value: value | null, verdict: Verdict }
```

### Request/response types
```jsonc
// Fact
{
  "id": "a1b2c3d4e5f6", "entity": "obj1", "predicate": "color", "value": "blue",
  "timestamp": 1751990400.0, "confidence": 0.95, "episode": "chat_001",
  "seq": 3, "expires_at": null, "derived_from": null
}

// WriteFact (request)
{ "entity": "obj1", "predicate": "color", "value": "blue",
  "confidence": 1.0, "episode": "chat_001", "ttl": null }

// ScoredFact = Fact + { "score": 0.87 }

// Episode
{ "opened_at": 1751990000.0, "closed_at": null, "tags": ["demo"] }

// VerifyReq
{ "known": { "color": "blue", "shape": "round" },
  "predicate": "size", "value": "small" }

// Verdict
{ "genuine": true, "veridicality": 1.0,
  "reason": "attested: forms a stored clique with the context" }

// ReconstructReq
{ "known": { "color": "blue", "shape": "round" }, "targets": ["size"] }
// -> { "size": "small" }   or on abstain -> { "size": null }

// GuardReq
{ "known": { "color": "blue", "shape": "round" },
  "predicate": "size", "candidate": "large" }
// -> { "value": null, "verdict": { "genuine": false, "veridicality": 0.5,
//       "reason": "unattested combination (possible confabulation)" } }
```

Notes for you:
- `value` can be any JSON scalar (usually string). Don't assume it's numeric.
- `veridicality` ∈ [0,1]. `genuine` = `veridicality >= threshold`; default
  threshold is `1.0`. Treat 1.0 as green, `0 < v < 1` as amber, `0` as red.
- `reconstruct` returns `null` for a target when the memory abstains — render
  that as an honest "no confident answer," never as an error.

## 7. Design direction

- **Feel:** a precise instrument. Calm neutrals, generous whitespace, monospace
  for ids/values, one confident accent color. Avoid gradients-for-drama.
- **Truth-signal color semantics (consistent everywhere):**
  green = attested/genuine, amber = unattested/uncertain, red = never-stored.
  Use these *only* for veridicality, so they read as a status language.
- **The Veridicality Meter** is the signature component — invest in it. A smooth
  0–100% gauge with the verdict badge and reason. It should feel authoritative.
- **Abstention is positive.** When the memory says "I don't know," style it as
  trustworthy restraint (a shield/🛡️ motif, neutral-calm), not a failure.
- **Confidence bars** (0–1) on facts: subtle, secondary.
- **Accessibility:** don't rely on color alone — pair each state with an icon +
  label. WCAG AA contrast. Full keyboard support on forms and chip inputs.
- **Light & dark themes**, respecting `prefers-color-scheme`.
- **Responsive:** works down to tablet; table collapses to cards on narrow.

Suggested microcopy:
- Genuine → "Attested — seen together in memory."
- Amber → "Possible confabulation — each part is real, but never together."
- Red → "Never stored — this value isn't in memory."
- Abstain → "No confident answer. The memory chose not to guess."

## 8. Tech constraints & definition of done

- **Stack:** your choice; React + TypeScript + Vite is a safe default. Keep it a
  single self-contained SPA. A small component library (e.g. shadcn/ui) is fine.
- **Mock-first:** ship with an in-memory mock API implementing §6 seeded from §9,
  togggleable to a real base URL via an env var (`VITE_API_BASE`). The app must be
  fully demoable with **no backend**.
- **No secrets, no external calls** beyond the configured API base. No auth needed
  for v1 (local dev tool).
- **State:** simple client state is fine (React Query/TanStack Query if fetching).
- **Done when:** all 7 screens work against the mock; the three verify states and
  the abstain state are each reachable via the preset examples; light/dark +
  keyboard + empty/loading/error states are handled; `npm run build` is clean.

Deliverables: the app, a short README (run + how to point at a real API), and the
mock data wired in.

## 9. Mock seed data (build against this)

Two entities forming a clean demo of every guard state:

```json
{
  "facts": [
    { "id": "f01", "entity": "obj1", "predicate": "color", "value": "blue",  "timestamp": 1751990400.0, "confidence": 1.0,  "episode": "demo", "seq": 0, "expires_at": null, "derived_from": null },
    { "id": "f02", "entity": "obj1", "predicate": "shape", "value": "round", "timestamp": 1751990400.0, "confidence": 1.0,  "episode": "demo", "seq": 1, "expires_at": null, "derived_from": null },
    { "id": "f03", "entity": "obj1", "predicate": "size",  "value": "small", "timestamp": 1751990400.0, "confidence": 0.9,  "episode": "demo", "seq": 2, "expires_at": null, "derived_from": null },
    { "id": "f04", "entity": "obj2", "predicate": "color", "value": "red",    "timestamp": 1751990500.0, "confidence": 1.0,  "episode": "demo", "seq": 3, "expires_at": null, "derived_from": null },
    { "id": "f05", "entity": "obj2", "predicate": "shape", "value": "square", "timestamp": 1751990500.0, "confidence": 1.0,  "episode": "demo", "seq": 4, "expires_at": null, "derived_from": null },
    { "id": "f06", "entity": "obj2", "predicate": "size",  "value": "large",  "timestamp": 1751990500.0, "confidence": 0.8,  "episode": "demo", "seq": 5, "expires_at": null, "derived_from": null }
  ],
  "episodes": { "demo": { "opened_at": 1751990000.0, "closed_at": null, "tags": ["demo"] } }
}
```

Mock behavior for the guard (implement this logic in the mock so the demo is live):
- Build, per entity, the set of its `(predicate,value)` cells; an edge exists
  between two cells if they appear in the **same** entity.
- `veridicality(cells)` = fraction of cell-pairs that share an edge; but **0.0 if
  any cell's value was never stored for that predicate**.
- `verify(known, predicate, value)` → veridicality of `known ∪ {(predicate,value)}`;
  `genuine = score >= 1.0`.
- `reconstruct(known, targets)` → for each target predicate, pick the value that
  forms a complete clique with all known cells; if none, return `null`.

Three preset examples to wire into the Verify screen:
1. **Genuine** → known `{color: blue, shape: round}`, claim `size = small`
   → `{ genuine: true, veridicality: 1.0, reason: "attested: forms a stored clique with the context" }`
2. **Never stored (red)** → known `{color: blue}`, claim `size = gigantic`
   → `{ genuine: false, veridicality: 0.0, reason: "value 'gigantic' never stored for 'size'" }`
3. **Ghost recombination (amber)** → known `{color: blue, shape: square}`, claim `size = large`
   → `{ genuine: false, veridicality: 0.5, reason: "unattested combination (possible confabulation)" }`

Reconstruct presets:
- Answerable → known `{color: blue, shape: round}`, target `size` → `{ size: "small" }`.
- Unanswerable → known `{color: blue, shape: square}`, target `size` → `{ size: null }` (abstain).

## 10. Out of scope (v1)

Auth/multi-user, persistence beyond the API, editing/deleting facts (memory is
append-only — no destructive UI), real-time sync, mobile-phone layouts, and the
enforcing (blocking) guard mode. Keep it a focused read/write/verify console.

---

*Backend note (not your job, for context): the four verify endpoints map 1:1 to
`dilmun.VeridicalityGuard` (`verify`, `verify_fact`, `reconstruct`, `guard`);
facts/context/graph/episodes map to `dilmun.DilmunMemory`. A ~100-line FastAPI
wrapper exposes them. Build against the mock; wiring the real API is a base-URL
swap.*
