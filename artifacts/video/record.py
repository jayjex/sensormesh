#!/usr/bin/env python3
"""
VoltHacks day 4: record the 90s SensorMesh walkthrough per docs/video-script.md.
Headed chromium on the proven Wayland pattern (headless weston session, WAYLAND_DISPLAY),
Playwright record_video screencast. One continuous take, 8 beats = ~90s.
All terminal content = real captured output from this repo (regenerated per run).
"""
import json, base64, os, re, subprocess, sys, time, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8018/dashboard/index.html"
API = "http://127.0.0.1:8793"
W, H = 1600, 900
OUT_DIR = "/tmp/smv"
REC_DIR = "/tmp/smvrec"
MCP_DIR = "/home/uwuki/sensormesh/mcp"

CSS = """
* { box-sizing: border-box; margin: 0; }
body { background:#0d1117; color:#e6edf3; font: 16px/1.55 'DejaVu Sans', sans-serif; }
.slide { position:fixed; inset:0; display:flex; flex-direction:column; padding:70px 90px 110px; }
.kicker { color:#3fb950; font-weight:700; letter-spacing:.14em; text-transform:uppercase; font-size:14px; }
h1 { font-size:52px; line-height:1.15; margin:14px 0 26px; }
.big { font-size:30px; line-height:1.5; color:#c9d1d9; }
.big b { color:#e6edf3; }
.accent { color:#d29922; }
.cap { position:fixed; left:0; right:0; bottom:0; height:84px; display:flex; align-items:center;
       justify-content:center; background:#161b22; border-top:1px solid #21262d;
       color:#c9d1d9; font-size:19px; padding:0 60px; text-align:center; }
.term { position:fixed; inset:0 0 84px 0; overflow:hidden; background:#0a0d12; padding:34px 44px;
        font:16.5px/1.62 'DejaVu Sans Mono', monospace; color:#c9d1d9; white-space:pre-wrap; word-break:break-all; }
.p { color:#7ee787 } .s402 { color:#d29922; font-weight:700 } .s200 { color:#3fb950; font-weight:700 }
.dim { color:#6e7681 } .hl { color:#a5d6ff } .k { color:#79c0ff }
"""

def page_shell(title, body, caption):
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{title}</title><style>{CSS}</style></head>
<body>{body}<div class="cap">{caption}</div></body></html>"""

# ---- beat 1: problem (plain text slide — script production notes allow it)
SLIDE_1 = page_shell("beat1", """
<div class="slide">
  <div class="kicker">the problem</div>
  <h1>Air quality data, behind a login</h1>
  <div class="big">Cities deploy street-level sensors, then put the readings behind
  <b>accounts and export queues</b>.</div>
  <div class="big" style="margin-top:26px">Typical open-data portal: sign in,
  <b>wait 48 hours</b>, get a CSV file.</div>
  <div class="big dim" style="margin-top:26px">Researchers just want the numbers.</div>
</div>""", "Cities deploy air quality sensors, then lock the readings behind a login.")

# ---- beat 2: simulator (real captured output)
SIM_CMD = "python3 simulator/simulate.py --seed 42 --out /tmp/smv/v42 --format csv"
sim_out = open("/tmp/smv/sim-out.txt").read().rstrip()
SLIDE_2 = page_shell("beat2", f"""
<div class="term" id="t"></div>
<script>
const cmd = {json.dumps(SIM_CMD)};
const out = {json.dumps(sim_out)};
const t = document.getElementById('t');
let i = 0, lines;
function start() {{
  t.innerHTML = '<span class="p">$</span> <b style="color:#e6edf3" id="cmd"></b><span id="cur">▊</span>';
  const el = document.getElementById('cmd');
  let j = 0;
  const iv = setInterval(() => {{
    el.textContent = cmd.slice(0, ++j);
    if (j >= cmd.length) {{ clearInterval(iv); reveal(); }}
  }}, 22);
}}
function reveal() {{
  document.getElementById('cur').remove();
  lines = out.split('\\n');
  let k = 0;
  const iv = setInterval(() => {{
    if (k >= lines.length) {{ clearInterval(iv); return; }}
    t.innerHTML += '\\n' + (k === 0 ? '' : '');
    t.innerHTML += '<span class="hl">' + lines[k].replace(/</g,'&lt;') + '</span>';
    k++;
  }}, 340);
}}
start();
</script>""", "One command regenerates a full day of readings — same seed, same data. 1,296 rows, 9 devices, 3 sites.")

# ---- beat 3: MCP query (real captured output)
mcp = json.load(open("/tmp/smv/mcp-out.json"))
row0 = json.dumps(mcp["page"][0], indent=1)
mcp_head = {k: mcp[k] for k in ("data_file", "sha256", "total_rows_in_file", "total_matched", "offset", "returned")}
MCP_CMD = 'query_readings({ site: "riverside-park", sensor: "noise", anomaly: "spike" })'
SLIDE_3 = page_shell("beat3", f"""
<div class="term" id="t"></div>
<script>
const cmd = {json.dumps(MCP_CMD)};
const outHead = {json.dumps(json.dumps(mcp_head, indent=1))};
const row0 = {json.dumps(row0)};
const tail = '\\n  … +2 more rows (total_matched: 3)\\n}}';
const t = document.getElementById('t');
let j = 0;
function start() {{
  t.innerHTML = '<span class="p">$</span> <b style="color:#e6edf3" id="cmd"></b><span id="cur">▊</span>';
  const el = document.getElementById('cmd');
  const iv = setInterval(() => {{
    el.textContent = cmd.slice(0, ++j);
    if (j >= cmd.length) {{ clearInterval(iv); reveal(); }}
  }}, 22);
}}
function reveal() {{
  document.getElementById('cur').remove();
  t.innerHTML += '\\n<span class="dim">→ mcp/index.js · stdio · tool call</span>\\n\\n';
  const parts = [outHead, row0];
  let k = 0;
  const iv = setInterval(() => {{
    if (k < parts.length) {{ t.innerHTML += '<span class="hl">' + parts[k].replace(/</g,'&lt;') + '</span>'; k++; }}
    else {{ clearInterval(iv); t.innerHTML += '<span class="s200">' + tail + '</span>'; }}
  }}, 1400);
}}
start();
</script>""", "Any LLM session queries the mesh over MCP. Every response pins the sha256 of its data file.")

# ---- beat 6: architecture (verbatim from README)
readme = open("/home/uwuki/sensormesh/README.md").read()
diagram = readme.split("```")[1].rstrip()
arch_body = f"""
<div class="slide" style="padding:40px 70px 110px">
  <div class="kicker">architecture</div>
  <div style="font:15.5px/1.5 'DejaVu Sans Mono', monospace; color:#c9d1d9; white-space:pre; margin-top:10px">{diagram}</div>
</div>"""
SLIDE_6 = page_shell("beat6", arch_body,
  "One query engine backs MCP and HTTP. Mock settlement is a seam — swap in a real facilitator and the same routes settle on-chain.")

# ---- beat 7: tiers
SLIDE_7 = page_shell("beat7", """
<div class="slide">
  <div class="kicker">three access tiers</div>
  <h1 style="margin-bottom:34px">One data file, three doors</h1>
  <div class="big" style="margin:14px 0"><b>Raw files</b> — free, in the repo (CSV + JSONL, sha256-pinned)</div>
  <div class="big" style="margin:14px 0"><b>MCP</b> — free, any LLM session (list_sensors · query_readings · get_stats)</div>
  <div class="big" style="margin:14px 0"><b>Metered HTTP</b> — <span class="accent">$0.001 per call</span>, x402 exact scheme, USDC on Base</div>
  <div class="big dim" style="margin-top:34px">Data is simulated for now. The schema is the deliverable —
  real devices can publish it unchanged.</div>
</div>""", "Raw files: free. MCP: free, any LLM. Metered HTTP: per-call pricing for apps that want an endpoint.")

# ---- beat 8: repo card
SLIDE_8 = page_shell("beat8", """
<div class="slide" style="justify-content:center; align-items:center; text-align:center">
  <div class="kicker" style="margin-bottom:8px">sensor mesh</div>
  <h1 style="font-size:58px">SensorMesh</h1>
  <div class="big" style="margin:10px 0 30px">The street's data, without the login.</div>
  <div style="font:26px 'DejaVu Sans Mono', monospace; color:#79c0ff; background:#161b22;
              border:1px solid #30363d; border-radius:10px; padding:18px 34px">github.com/jayjex/sensormesh</div>
  <div class="big dim" style="margin-top:26px">MIT license · clone it, run it, query it</div>
</div>""", "Clone it, run it, query it. SensorMesh: the street's data, without the login.")

for name, html in [("slide-1.html", SLIDE_1), ("slide-2.html", SLIDE_2), ("slide-3.html", SLIDE_3),
                   ("slide-6.html", SLIDE_6), ("slide-7.html", SLIDE_7), ("slide-8.html", SLIDE_8)]:
    open(f"{OUT_DIR}/{name}", "w").write(html)
print("slides written")

CAPTION_CSS = """
<div style="position:fixed;left:0;right:0;bottom:0;height:84px;display:flex;align-items:center;justify-content:center;background:#161b22;border-top:1px solid #21262d;color:#c9d1d9;font-size:19px;padding:0 60px;text-align:center;z-index:9999" id="vcap"></div>
<style>body{padding-bottom:84px}</style>
"""

def goto_cap(page, text):
    page.evaluate(f"""() => {{
        let el = document.getElementById('vcap');
        if (!el) {{ document.body.insertAdjacentHTML('beforeend', {json.dumps(CAPTION_CSS)}); el = document.getElementById('vcap'); }}
        el.textContent = {json.dumps(text)};
    }}""")

def run():
    os.makedirs(REC_DIR, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()  # headed — renders on the Wayland session
        ctx = browser.new_context(
            viewport={"width": W, "height": H},
            record_video_dir=REC_DIR,
            record_video_size={"width": W, "height": H},
        )
        pg = ctx.new_page()
        t0 = time.time()
        beat = lambda n: print(f"[{time.time()-t0:6.1f}s] beat {n}", flush=True)

        # beat 1 — problem slide, 10s
        beat(1); pg.goto("file:///tmp/smv/slide-1.html"); pg.wait_for_timeout(10000)

        # beat 2 — simulator terminal, 10s (typed + real output)
        beat(2); pg.goto("file:///tmp/smv/slide-2.html"); pg.wait_for_timeout(10000)

        # beat 3 — MCP query terminal, 10s
        beat(3); pg.goto("file:///tmp/smv/slide-3.html"); pg.wait_for_timeout(10000)

        # beat 4 — dashboard loads + charts settle, 10s
        beat(4); pg.goto(BASE)
        pg.wait_for_selector(".dataset-row", timeout=20000)
        pg.wait_for_timeout(2500)  # charts draw
        goto_cap(pg, "The dashboard reads the same file: time series, per-site means, anomaly counts, CSV export.")
        pg.wait_for_timeout(7500)

        # beat 5 — buy flow: 402 → sign → 200, 20s
        beat(5)
        pg.locator(".x402-head").first.scroll_into_view_if_needed()
        pg.wait_for_timeout(2500)
        goto_cap(pg, "Metered HTTP over x402: 402 with the price → sign → 200 with data + settlement receipt. Dev build: settlement mocked.")
        pg.wait_for_timeout(2500)
        pg.click("#buy")
        pg.wait_for_timeout(12000)  # let the flow land and breathe — the money shot

        # beat 6 — architecture, 12s
        beat(6); pg.goto("file:///tmp/smv/slide-6.html"); pg.wait_for_timeout(12000)

        # beat 7 — tiers, 12s
        beat(7); pg.goto("file:///tmp/smv/slide-7.html"); pg.wait_for_timeout(12000)

        # beat 8 — repo card, 6s
        beat(8); pg.goto("file:///tmp/smv/slide-8.html"); pg.wait_for_timeout(6000)

        pg.close()
        ctx.close()
        browser.close()
        print(f"total {time.time()-t0:.1f}s", flush=True)

    vids = [f for f in os.listdir(REC_DIR) if f.endswith(".webm")]
    print("recordings:", vids)
    return [os.path.join(REC_DIR, v) for v in vids]

if __name__ == "__main__":
    run()
