/**
 * Dilmun × Pi extension — gives the pi.dev agent two tools, backed by the Dilmun
 * bridge. The vetted-source guarantee lives in the BRIDGE, so the agent only has
 * to decide WHAT to look up — it never has to know how to search the web, which
 * sources are allowed, or how to parse them. A "stupid" harness is fine.
 *
 *   dilmun_acquire(query) — look a term up in VETTED sources (PubChem, openFDA,
 *                           OpenAlex) and WRITE the resulting facts into memory.
 *   dilmun_recall(query)  — retrieve what memory already knows (ranked).
 *
 * Setup: see PI-SETUP.md. Start the bridge first (node instrument/server.mjs).
 * Point the bridge at a different host/port with DILMUN_BRIDGE if needed.
 *
 * NOTE: written to the documented pi.dev extension API (default export factory +
 * pi.registerTool). If your Pi build wants TypeBox schemas, wrap `parameters`
 * with Type.Object(...); the shape below is a plain JSON schema.
 */
const BRIDGE = process.env.DILMUN_BRIDGE || "http://127.0.0.1:8420";

async function bridge(path) {
  const r = await fetch(BRIDGE + path);
  if (!r.ok) throw new Error("dilmun bridge " + r.status + " — is `node instrument/server.mjs` running?");
  return r.json();
}

export default function (pi) {
  pi.registerTool({
    name: "dilmun_acquire",
    label: "Dilmun · acquire",
    description:
      "Look up a term in VETTED academic/government sources (PubChem, openFDA, OpenAlex) and write the resulting facts into Dilmun memory. " +
      "Use this whenever you need a real, cited fact about an entity, compound, drug, or concept. " +
      "Only vetted sources are used; if none has it, nothing is written and the guard abstains.",
    parameters: {
      type: "object",
      properties: { query: { type: "string", description: "the entity or term to look up, e.g. 'epinephrine', 'anthropology'" } },
      required: ["query"],
    },
    async execute(_id, params) {
      try {
        const d = await bridge("/acquire?q=" + encodeURIComponent(params.query));
        const text = d.added > 0
          ? `Collected ${d.added} facts on "${params.query}" from ${d.sources.join(", ")}. Memory now holds ${d.facts.length} facts.`
          : `No vetted source returned facts for "${params.query}". Nothing written (guard abstained).`;
        return { content: [{ type: "text", text }], details: { added: d.added, sources: d.sources, vault: d.facts.length } };
      } catch (e) {
        return { content: [{ type: "text", text: String(e.message || e) }], isError: true };
      }
    },
  });

  pi.registerTool({
    name: "dilmun_recall",
    label: "Dilmun · recall",
    description:
      "Retrieve what Dilmun memory already knows about a query, ranked by confidence and recency. " +
      "Call this BEFORE acquiring, so you don't re-look-up facts already in memory.",
    parameters: {
      type: "object",
      properties: { query: { type: "string", description: "what to recall; empty returns the most salient facts" } },
      required: ["query"],
    },
    async execute(_id, params) {
      try {
        const d = await bridge("/recall?q=" + encodeURIComponent(params.query || ""));
        const lines = (d.results || []).map(f => `${(f.score ?? 0).toFixed(3)}  ${f.entity}.${f.predicate} = ${f.value}  [${f.source || "derived"}]`);
        return { content: [{ type: "text", text: lines.join("\n") || "(nothing in memory yet)" }], details: { count: (d.results || []).length } };
      } catch (e) {
        return { content: [{ type: "text", text: String(e.message || e) }], isError: true };
      }
    },
  });
}
