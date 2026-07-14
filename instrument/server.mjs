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
  try {
    const html = readFileSync(join(__dir, "dilmun-instrument.html"));
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.end(html);
  } catch {
    res.statusCode = 500;
    res.end("dilmun-instrument.html not found next to server.mjs");
  }
});

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
