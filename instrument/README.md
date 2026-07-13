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

Three sources run Dilmun's real operators (1:1 JS port of
`dilmun-memory-middleware/dilmun/operators.py`):

- **JEMHopQA (REAL)** — dev-split triples; compose derives the multi-hop
  answers, 4/4 match gold, proof chains clickable.
- **ROBOT TELEMETRY (SYNTH)** — Intel-Lab-schema stream; canonicalize keeps
  current values, forget drops noise/expired, retrieval shows score
  decomposition vs the vector-baseline recall of 0.245 (results.json).
- **PI MISSION (LIVE-SHAPED)** — a fact-acquisition mission in pi.dev event
  shapes: web fetch → dilmun_write → self-check contradiction → forget rumor
  → temporal world model ("elapsed = t₁ − t₀, computed not hallucinated").

Bottom strip: real benchmark receipts from `dilmun-memory-middleware/benchmarks/`.

The same HTML is published as a claude.ai artifact for sharing; terminals
only go live when served by this bridge (artifact CSP blocks WebSockets).
