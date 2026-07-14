#!/usr/bin/env node
/**
 * Dilmun instrument bridge — serves the memory-instrument UI and tile-managed
 * shell sessions over WebSocket. Zero dependencies: hand-rolled WS framing,
 * and a real PTY on Linux via util-linux `script` (no node-pty build step).
 *
 *   node instrument/server.mjs          → http://127.0.0.1:8420  (ws: /term)
 *
 * Each "+ TILE" in the UI opens one WebSocket → one shell. Closing the tile
 * kills the shell. Protocol: JSON text frames
 *   client → server  {type:"input", data:"<keys>"}
 *   server → client  {type:"meta", shell, pid} | {type:"output", data} | {type:"exit", code}
 */
import { createServer } from "node:http";
import { createHash } from "node:crypto";
import { spawn } from "node:child_process";
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const PORT = Number(process.env.DILMUN_PORT || 8420);
const HOST = "127.0.0.1"; // local shells: never bind beyond loopback
const __dir = dirname(fileURLToPath(import.meta.url));
const WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";

/* ── http: serve the instrument ── */
const server = createServer((req, res) => {
  if (req.url === "/health") { res.end("ok"); return; }
  if (req.url.startsWith("/acquire")) { handleAcquire(req, res); return; }
  try {
    const html = readFileSync(join(__dir, "dilmun-instrument.html"));
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.end(html);
  } catch {
    res.statusCode = 500;
    res.end("dilmun-instrument.html not found next to server.mjs");
  }
});

/* ── live acquisition: ask a term, get real facts from VETTED sources only ──
   PubChem + openFDA (gov) and OpenAlex (open science) so any reasonable term
   returns structured, sourced facts. This is the seam the pi.dev harness plugs
   into: swap harvest() for a `pi` RPC call whose dilmun_write_fact tool is
   restricted to this same allowlist, and the console drives Pi instead. */
async function jget(url, timeout = 8000) {
  const ac = new AbortController();
  const t = setTimeout(() => ac.abort(), timeout);
  try {
    const r = await fetch(url, { headers: { "User-Agent": "dilmun-instrument/0.1", "Accept": "application/json" }, signal: ac.signal });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return await r.json();
  } finally { clearTimeout(t); }
}

async function harvest(q) {
  const facts = [], hit = new Set();
  const enc = encodeURIComponent(q);
  // PubChem — compound (NIH·NLM, gov)
  try {
    const d = await jget(`https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/${enc}/property/MolecularFormula,MolecularWeight/JSON`);
    const p = d.PropertyTable.Properties[0];
    facts.push({ entity: q, predicate: "molecular_formula", value: p.MolecularFormula, source: "pubchem", confidence: 0.98 });
    facts.push({ entity: q, predicate: "molecular_weight", value: String(p.MolecularWeight), source: "pubchem", confidence: 0.98 });
    facts.push({ entity: q, predicate: "pubchem_cid", value: String(p.CID), source: "pubchem", confidence: 0.98 });
    hit.add("pubchem");
  } catch {}
  // openFDA — drug label (US FDA, gov)
  try {
    const d = await jget(`https://api.fda.gov/drug/label.json?search=openfda.generic_name:${enc}&limit=1`);
    const r = d.results[0], of = r.openfda || {};
    if (of.pharm_class_epc) facts.push({ entity: "med:" + q, predicate: "drug_class", value: of.pharm_class_epc[0], source: "openfda", confidence: 0.9 });
    if (r.indications_and_usage) facts.push({ entity: "med:" + q, predicate: "indication", value: r.indications_and_usage[0].replace(/\s+/g, " ").slice(0, 90), source: "openfda", confidence: 0.85 });
    if (of.route) facts.push({ entity: "med:" + q, predicate: "route", value: of.route[0], source: "openfda", confidence: 0.9 });
    if (facts.some(f => f.source === "openfda")) hit.add("openfda");
  } catch {}
  // OpenAlex — any academic concept/topic (open science). the general fallback.
  try {
    const d = await jget(`https://api.openalex.org/concepts?search=${enc}&per-page=1`);
    const c = d.results && d.results[0];
    if (c) {
      facts.push({ entity: q, predicate: "type", value: "academic_concept", source: "openalex", confidence: 0.9 });
      facts.push({ entity: q, predicate: "field_level", value: String(c.level), source: "openalex", confidence: 0.85 });
      facts.push({ entity: q, predicate: "works_count", value: String(c.works_count), source: "openalex", confidence: 0.9 });
      if (c.description) facts.push({ entity: q, predicate: "description", value: c.description.replace(/\s+/g, " ").slice(0, 90), source: "openalex", confidence: 0.8 });
      for (const rc of (c.related_concepts || []).slice(0, 3))
        facts.push({ entity: q, predicate: "related", value: String(rc.display_name).toLowerCase().replace(/\s+/g, "_"), source: "openalex", confidence: 0.75 });
      hit.add("openalex");
    }
  } catch {}
  return { facts, sources: [...hit] };
}

async function handleAcquire(req, res) {
  const q = (new URL(req.url, "http://x").searchParams.get("q") || "").trim();
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Access-Control-Allow-Origin", "*");
  if (!q) { res.end(JSON.stringify({ facts: [], sources: [] })); return; }
  try { res.end(JSON.stringify(await harvest(q))); }
  catch (e) { res.end(JSON.stringify({ facts: [], sources: [], error: String(e.message || e) })); }
}

/* ── ws upgrade: one socket = one shell ── */
server.on("upgrade", (req, sock) => {
  if (!req.url.startsWith("/term")) { sock.destroy(); return; }
  const accept = createHash("sha1").update(req.headers["sec-websocket-key"] + WS_GUID).digest("base64");
  sock.write(
    "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n" +
    `Sec-WebSocket-Accept: ${accept}\r\n\r\n`
  );
  attach(sock);
});

/* ── ws frame helpers (text frames only; server→client is unmasked) ── */
function frame(data) {
  const buf = Buffer.from(data);
  let head;
  if (buf.length < 126) head = Buffer.from([0x81, buf.length]);
  else if (buf.length < 65536) { head = Buffer.alloc(4); head[0] = 0x81; head[1] = 126; head.writeUInt16BE(buf.length, 2); }
  else { head = Buffer.alloc(10); head[0] = 0x81; head[1] = 127; head.writeBigUInt64BE(BigInt(buf.length), 2); }
  return Buffer.concat([head, buf]);
}

function attach(sock) {
  const { label, proc } = spawnShell();
  const send = obj => { try { sock.write(frame(JSON.stringify(obj))); } catch {} };
  const kill = () => { try { proc.kill(); } catch {} };

  send({ type: "meta", shell: label, pid: proc.pid });
  proc.stdout.on("data", d => send({ type: "output", data: d.toString("utf8") }));
  proc.stderr && proc.stderr.on("data", d => send({ type: "output", data: d.toString("utf8") }));
  proc.on("exit", code => { send({ type: "exit", code }); try { sock.end(); } catch {} });

  let acc = Buffer.alloc(0);
  sock.on("data", chunk => {
    acc = Buffer.concat([acc, chunk]);
    while (true) {
      if (acc.length < 2) break;
      const op = acc[0] & 0x0f;
      let len = acc[1] & 0x7f, off = 2;
      if (len === 126) { if (acc.length < 4) break; len = acc.readUInt16BE(2); off = 4; }
      else if (len === 127) { if (acc.length < 10) break; len = Number(acc.readBigUInt64BE(2)); off = 10; }
      const masked = acc[1] & 0x80;
      const mask = masked ? acc.subarray(off, off + 4) : null;
      if (masked) off += 4;
      if (acc.length < off + len) break;
      let payload = acc.subarray(off, off + len);
      if (mask) { payload = Buffer.from(payload); for (let i = 0; i < payload.length; i++) payload[i] ^= mask[i % 4]; }
      acc = acc.subarray(off + len);
      if (op === 8) { kill(); try { sock.end(); } catch {} return; }          // close
      if (op === 9) { try { sock.write(Buffer.concat([Buffer.from([0x8a, payload.length]), payload])); } catch {} continue; } // ping→pong
      if (op === 1) {
        try {
          const m = JSON.parse(payload.toString("utf8"));
          if (m.type === "input") proc.stdin.write(m.data);
        } catch {}
      }
    }
  });
  sock.on("close", kill);
  sock.on("error", kill);
}

/* ── shell spawn — linux-tuned: real PTY via `script`, graceful fallbacks ── */
function spawnShell() {
  const env = { ...process.env, TERM: "xterm-256color" };
  if (process.platform === "linux") {
    const sh = process.env.SHELL || "/bin/bash";
    for (const bin of ["/usr/bin/script", "/bin/script"]) {
      if (existsSync(bin)) {
        // util-linux `script` allocates a pty → echo, colors, ctrl-c, job control
        return { label: sh.split("/").pop() + " (pty)", proc: spawn(bin, ["-qfc", sh, "/dev/null"], { env }) };
      }
    }
    return { label: sh.split("/").pop() + " (pipe)", proc: spawn(sh, ["-i"], { env }) };
  }
  if (process.platform === "darwin") {
    const sh = process.env.SHELL || "/bin/zsh";
    return { label: sh.split("/").pop() + " (pipe)", proc: spawn(sh, ["-i"], { env }) };
  }
  // windows — pipe mode, mainly for testing the bridge off-linux
  return { label: "powershell (pipe)", proc: spawn("powershell.exe", ["-NoLogo"], { env }) };
}

server.listen(PORT, HOST, () =>
  console.log(`dilmun instrument bridge → http://${HOST}:${PORT}   (shells via ws /term)`));
