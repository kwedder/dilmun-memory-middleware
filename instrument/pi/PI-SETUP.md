# Connecting pi.dev to Dilmun (live vetted acquisition)

**The key idea:** the search smarts live in the **bridge**, not in Pi. The bridge
does the vetted-source lookup, canonicalizes, and stores the facts. Pi only has to
decide *what* to look up and hit one URL. Your harness does **not** need a
web-search tool, source allowlists, or fact parsing — it just calls the bridge.

Start the bridge once (it holds the shared memory both Pi and the UI use):

```sh
node instrument/server.mjs        # → http://127.0.0.1:8420
```

The bridge exposes:

| endpoint | what it does |
|---|---|
| `GET /acquire?q=<term>` | look `<term>` up in VETTED sources (PubChem, openFDA, OpenAlex), write facts to the shared vault, return them |
| `GET /recall?q=<term>`  | retrieve ranked facts already in memory |
| `GET /facts`            | dump the whole canonical vault |
| `GET /forget`           | clear the vault |

Everything written is vetted-only and canonicalized — enforced server-side, so it
can't be bypassed by a confused agent.

---

## Path A — for a "stupid" harness: just curl (works with ANY harness)

Every agent harness has a shell. Add this to Pi's project instructions
(`.pi/AGENTS.md` or `CLAUDE.md`, or the system prompt) and you're done:

```markdown
## Memory (Dilmun)
You have a persistent memory served at http://127.0.0.1:8420. To learn or store a
fact, DO NOT guess — run:
    curl -s "http://127.0.0.1:8420/acquire?q=<term>"
It searches vetted academic/government sources and stores the facts. To check what
you already know:
    curl -s "http://127.0.0.1:8420/recall?q=<term>"
Only use these for facts. If /acquire returns "added": 0, no vetted source had it —
say so; do not invent the answer.
```

That's the whole integration. Pi uses its normal bash tool to curl the bridge; the
bridge does the rest. Test it yourself the same way Pi will:

```sh
curl -s "http://127.0.0.1:8420/acquire?q=anthropology"
curl -s "http://127.0.0.1:8420/recall?q=anthropology"
```

## Path B — cleaner: load the extension (typed tools)

If you'd rather Pi have real named tools (`dilmun_acquire`, `dilmun_recall`)
instead of curl, load `instrument/pi/dilmun-extension.mjs`. In your Pi settings
(`~/.pi/agent/settings.json` global, or `.pi/settings.json` project):

```json
{ "extensions": ["./instrument/pi/dilmun-extension.mjs"] }
```

(The exact key depends on your Pi version — check `pi --help` / the docs for how
your build loads extensions; some use `extensionFactories` in the SDK or a
`--extension` flag. The file is a standard default-export factory.)

Override the bridge location with `DILMUN_BRIDGE=http://host:port` if it isn't on
the default port.

---

## Path C — run Pi *inside* the frontend (the "pi version")

Open `http://127.0.0.1:8420` and click **+ PI HARNESS** in the terminal panel. The
bridge launches the `pi` CLI in a terminal tile, from the repo root, with
`DILMUN_BRIDGE` already set. You talk to Pi in that tile; whatever it acquires
lands in the shared vault and appears in the ACQUIRE universe live. Requires `pi`
on PATH (`npm i -g @earendil-works/pi-coding-agent`, or set `DILMUN_PI` to its
path). Combine with Path A: put the curl instructions in `.pi/AGENTS.md` so Pi
running in the tile knows to use the bridge for facts.

## Watching it happen

Open `http://127.0.0.1:8420` in a browser while Pi runs (in the + PI HARNESS tile,
or separately). The **ACQUIRE** universe polls the shared vault every few seconds,
so whatever Pi collects appears as facts condensing in real time — you're
literally watching the harness build memory.

## Making it *Pi's own* web search (later)

Right now `/acquire` is a deterministic harvester over three vetted APIs. To make
it Pi doing open-ended reasoning-driven search instead, replace `harvest()` in
`server.mjs` with a `pi` RPC run whose own web-search tool is restricted to the
same vetted allowlist. Same endpoint, same guarantees — Pi just chooses the
sources within the allowlist. The frontend and this setup don't change.
