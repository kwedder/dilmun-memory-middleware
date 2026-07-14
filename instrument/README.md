# Dilmun Memory Instrument

Standalone pre-demo UI + local bridge. No build step, no dependencies.

## Run (Linux)

```sh
node instrument/server.mjs
# → http://127.0.0.1:8420
```

Open the URL, click **+ TILE** in the Terminals panel (right rail) to spawn
tile-managed local shells. Each tile is one shell; tiles split the column
evenly; × kills the shell.

- On Linux the bridge allocates a real PTY via util-linux `script`
  (echo, colors, Ctrl-C, arrows, history all work).
- Fallback is pipe mode (the tile does local echo; line-based).
- Bound to 127.0.0.1 only — shells are never exposed off-machine.
- `DILMUN_PORT=9000 node instrument/server.mjs` to change port.

## What the UI shows

Everything runs Dilmun's real operators (1:1 JS port of `dilmun/operators.py`).

**ACQUIRE** (primary tab) — memory acquisition. Ask it to look something up in
the ask box; it draws **only from vetted academic/government sources** (PubChem,
openFDA, PubMed, D-PLACE, OpenAlex, Scholar) and refuses — *guard · abstain* —
when no vetted source carries the ask. Facts condense, canonicalize, and compose
cross-domain (a drug's moiety → its compound → its formula). This is the surface
the **Pi terminal will drive** once the harness is wired; the vetted allowlist
matches `benchmarks/nabu/vetted_sources.json`.

**TESTING** (grouped dropdown) — three demos:

- **JEMHopQA (REAL)** — dev-split triples; compose derives the multi-hop
  answers, 4/4 match gold, proof chains clickable.
- **ROBOT TELEMETRY (SYNTH)** — Intel-Lab-schema stream; canonicalize keeps
  current values, forget drops noise/expired, retrieval shows score
  decomposition vs the vector-baseline recall of 0.245 (results.json).
- **PI MISSION (LIVE-SHAPED)** — a fact-acquisition mission in pi.dev event
  shapes: web fetch → dilmun_write → self-check contradiction → forget rumor
  → temporal world model ("elapsed = t₁ − t₀, computed not hallucinated").

Bottom strip: real benchmark receipts from `benchmarks/`.

### Performance

The canvas is idle-aware: it stops repainting when nothing is animating, and
**freezes entirely while a terminal tile is focused** so the integrated shell
stays responsive. Rotation defaults **off** (toggle in the VIEW controls) for a
calm, low-CPU scene; ORTHOGONAL gives a static axis-aligned view.

The same HTML is published as a claude.ai artifact for sharing; terminals only
go live when served by this bridge (artifact CSP blocks WebSockets).
