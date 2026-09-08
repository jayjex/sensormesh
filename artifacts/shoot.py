#!/usr/bin/env python3
"""Screenshot harness for SensorMesh (playwright, pwenv venv)."""
import sys, time
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8018/index.html"
OUT = "/home/uwuki/sensormesh/artifacts/sensormesh-shots"

def shot(page, path, clip=None):
    page.wait_for_timeout(400)
    page.screenshot(path=path, clip=clip)
    print("saved", path)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 980}, device_scale_factor=2)
    pg.goto(BASE)
    pg.wait_for_selector(".dataset-row", timeout=15000)
    pg.wait_for_timeout(1200)  # charts settle

    # 1. full dashboard
    shot(pg, f"{OUT}/01-dashboard-full.png")

    # tall viewport so the x402 section is fully on-page for clipping
    pg.set_viewport_size({"width": 1440, "height": 2600})
    pg.wait_for_timeout(400)
    x402 = pg.locator(".x402-head").bounding_box()

    # run the flow once to get the final section height (terminal grows),
    # then take all three x402 shots with that clip
    pg.click("#buy")
    pg.wait_for_selector("#rows-wrap:not([hidden])", timeout=10000)
    pg.wait_for_timeout(600)
    bottom = pg.locator(".term").bounding_box()
    clip = {"x": 0, "y": x402["y"] - 8, "width": 1440,
            "height": bottom["y"] + bottom["height"] - x402["y"] + 16}

    # 4. final flow state (200 + settlement)
    shot(pg, f"{OUT}/04-x402-flow-200.png", clip=clip)

    # 2. idle section — reload, clean state
    pg.goto(BASE)
    pg.wait_for_selector(".dataset-row", timeout=15000)
    pg.wait_for_timeout(1000)
    shot(pg, f"{OUT}/02-x402-section.png", clip=clip)

    # 3. mid-flow (402 requirements visible, payment signed)
    pg.click("#buy")
    pg.wait_for_selector(".jsonbox", timeout=10000)
    pg.wait_for_timeout(350)
    shot(pg, f"{OUT}/03-x402-flow-402.png", clip=clip)

    # 4. MCP terminal — values are real output from mcp/lib/query.js against
    #    data/sensormesh-sample.csv (seed 42): riverside-park noise spikes,
    #    air_quality stats.
    pg2 = b.new_page(viewport={"width": 980, "height": 560}, device_scale_factor=2)
    pg2.goto("data:text/html,<title>mcp</title>")
    pg2.evaluate("""() => {
      document.body.style.cssText = 'margin:0;background:#0d1117;color:#e6edf3;' +
        'font:13px/1.65 ui-monospace,Menlo,Consolas,monospace;padding:22px 26px;' +
        'white-space:pre-wrap';
      const t = document.createElement('div');
      t.innerHTML = `<span style="color:#7ee787">$</span> <b style="color:#e6edf3">claude</b> <span style="color:#8b949e"># any LLM session with the sensormesh MCP server</span>\\n` +
        `<span style="color:#7ee787">&gt;</span> query_readings({ site: "riverside-park", sensor: "noise", anomaly: "spike", limit: 3 })\\n\\n` +
        `<span style="color:#8b949e">mcp: sensormesh · tool: query_readings</span>\\n` +
        `total_matched: <span style="color:#f2cc60">3</span>  sha256: 022b54f9…a1197\\n` +
        `[\\n  { timestamp: "2026-09-08T00:00:00Z", device_id: "sm-006", site: "riverside-park",\\n` +
        `    sensor_type: "noise", value: <span style="color:#f2cc60">65.2</span>, unit: "dB", anomaly: "spike" },\\n` +
        `  { timestamp: "2026-09-08T06:20:00Z", device_id: "sm-006", site: "riverside-park",\\n` +
        `    sensor_type: "noise", value: <span style="color:#f2cc60">67.3</span>, unit: "dB", anomaly: "spike" },\\n` +
        `  { timestamp: "2026-09-08T11:40:00Z", device_id: "sm-006", site: "riverside-park",\\n` +
        `    sensor_type: "noise", value: <span style="color:#f2cc60">80.8</span>, unit: "dB", anomaly: "spike" }\\n]\\n\\n` +
        `<span style="color:#7ee787">$</span> <b style="color:#e6edf3">claude</b>\\n` +
        `<span style="color:#7ee787\">&gt;</span> get_stats({ sensor: "air_quality" })\\n\\n` +
        `<span style=\"color:#8b949e\">air_quality · 432 readings · min 0 / mean 23.15 / max 126.7 ug/m3 · anomalies: 2 spikes, 1 flatline</span>\\n\\n` +
        `<span style="color:#8b949e">same query engine, same sha-pinned data file as the x402 HTTP API.</span>`;
      document.body.appendChild(t);
    }""")
    pg2.wait_for_timeout(300)
    shot(pg2, f"{OUT}/05-mcp-terminal.png")

    b.close()
print("done")
