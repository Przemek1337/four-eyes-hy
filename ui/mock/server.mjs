// Runs the mock admin API over HTTP on 127.0.0.1:8080 (the port the real gateway uses), with a live event stream
// and a small control page at /__mock/. Plain Node, no dependencies:  npm run mock
import http from "node:http";
import { pathToFileURL } from "node:url";
import { createMock } from "./handler.mjs";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const CONTROL_PAGE = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FourEyes mock gateway</title>
<style>
  :root{color-scheme:dark} body{margin:0;background:#0a0a0a;color:#f5f5f2;font:15px/1.6 system-ui,sans-serif;padding:48px 24px;max-width:640px}
  h1{font-size:28px;letter-spacing:-.02em;margin:0 0 4px} p{color:#a3a39e;margin:0 0 28px}
  .row{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:16px 0;border-top:1px solid #262626}
  .row b{display:block} .row span{color:#a3a39e;font-size:14px}
  button{font:inherit;border-radius:999px;border:1px solid #7e7e79;background:none;color:inherit;padding:8px 20px;cursor:pointer}
  button[aria-pressed=true]{background:#c8f560;border-color:#c8f560;color:#0a0a0a;font-weight:600}
  a{color:#c8f560}
</style></head><body>
<h1>Mock gateway</h1><p>Made-up data for the dashboard. <a href="http://127.0.0.1:5173/ui/">Open the dashboard</a>.</p>
<div id="rows"></div>
<div class="row"><div><b>Reset</b><span>Back to the starting state, and forget decisions and chats.</span></div><button id="reset">Reset</button></div>
<script>
const ITEMS=[["removed","A control was removed","Posture drops, the controls table, OWASP tile and policy history change, an alert appears."],
 ["slow","Slow gateway","Every answer takes 2.5 s, so you see the loading skeletons."],
 ["fail","Gateway down","Every request fails with 503: errors with Retry, then the offline banner."]];
const rows=document.getElementById("rows");
function draw(s){rows.innerHTML="";for(const [k,t,d] of ITEMS){const r=document.createElement("div");r.className="row";
 r.innerHTML="<div><b>"+t+"</b><span>"+d+"</span></div>";const b=document.createElement("button");b.textContent=s[k]?"On":"Off";b.setAttribute("aria-pressed",String(!!s[k]));
 b.onclick=async()=>{await fetch("/__mock/toggle-"+k);load()};r.appendChild(b);rows.appendChild(r)}}
async function load(){draw(await (await fetch("/__mock/state")).json())}
document.getElementById("reset").onclick=async()=>{await fetch("/__mock/reset");load()};
load();
</script></body></html>`;

export function startServer({ port = Number(process.env.MOCK_PORT ?? 8080), host = "127.0.0.1", now } = {}) {
  const mock = createMock(now ? { now } : {});
  const streams = new Set();
  const broadcast = (event) => { for (const res of streams) res.write(`data: ${JSON.stringify(event)}\n\n`); };

  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url ?? "/", "http://mock");
    if (url.pathname === "/admin/stream") {
      res.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-cache", Connection: "keep-alive" });
      res.write(": connected\n\n");
      streams.add(res);
      const ping = setInterval(() => res.write(": ping\n\n"), 15000);
      req.on("close", () => { clearInterval(ping); streams.delete(res); });
      return;
    }
    if (url.pathname === "/__mock" || url.pathname === "/__mock/") {
      res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
      res.end(CONTROL_PAGE);
      return;
    }
    let body = {};
    if (req.method === "POST") {
      const chunks = [];
      for await (const c of req) chunks.push(c);
      try { body = JSON.parse(Buffer.concat(chunks).toString() || "{}"); } catch { body = {}; }
    }
    const r = mock.handle(req.method ?? "GET", req.url ?? "/", body);
    if (r.delayMs) await sleep(r.delayMs);
    if (r.raw !== undefined) {
      res.writeHead(r.status, { "Content-Type": r.contentType ?? "text/plain", "Content-Disposition": `attachment; filename=${r.filename ?? "export.txt"}` });
      res.end(r.raw);
    } else {
      res.writeHead(r.status, { "Content-Type": "application/json" });
      res.end(JSON.stringify(r.body ?? {}));
    }
    if (r.broadcast) broadcast({ event: "decision" });
  });
  return new Promise((resolve) => server.listen(port, host, () => resolve({ server, mock, port: server.address().port, close: () => { for (const s of streams) s.end(); server.close(); } })));
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  const { port } = await startServer();
  console.log(`Mock gateway on http://127.0.0.1:${port}  (controls: http://127.0.0.1:${port}/__mock/)`);
}
