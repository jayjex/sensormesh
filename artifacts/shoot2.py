#!/usr/bin/env python3
"""Shots 6+7: curl 402/200 terminal (real output from r402.txt/r200.txt) and repo tree."""
from playwright.sync_api import sync_playwright

OUT = "/home/uwuki/sensormesh/artifacts/sensormesh-shots"
R402 = open("/tmp/r402.txt").read()
R200 = open("/tmp/r200.txt").read()

def pick(txt, keep):
    """Keep only the header lines we care about, preserving order/content."""
    lines = [l.rstrip() for l in txt.splitlines()]
    return [l for l in lines if any(l.lower().startswith(k) for k in keep)]

drop_headers = ("access-control", "etag", "date:", "connection", "keep-alive", "content-length",
                "content-type", "x-powered-by")
req_h = [l for l in pick(R402, ("http/1.1", "x-payment:"))]
req_body = R402.split("\r\n\r\n")[-1].split("\n\n")[-1].strip()
res_h = [l for l in pick(R200, ("http/1.1", "x-payment-response:"))]
res_body = R200.split("\r\n\r\n")[-1].split("\n\n")[-1].strip()

def trunc(s, n): return s if len(s) <= n else s[:n] + "…"
req_body = trunc(req_body, 700)
res_body = trunc(res_body, 900)

html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
body {{ margin:0; background:#0d1117; color:#c9d1d9; font:13px/1.6 ui-monospace,Menlo,Consolas,monospace; padding:22px 26px; white-space:pre-wrap; word-break:break-all; }}
.p {{ color:#7ee787 }} .s402 {{ color:#d29922; font-weight:700 }} .s200 {{ color:#3fb950; font-weight:700 }}
.dim {{ color:#6e7681 }} .hl {{ color:#a5d6ff }}
</style></head><body>
<span class="p">$</span> <b style="color:#e6edf3">curl -i</b> "http://localhost:8793/v1/readings?sensor=noise&amp;limit=2"
{req_h[0].replace('HTTP/1.1 402 Payment Required', '<span class="s402">HTTP/1.1 402 Payment Required</span>')}
<span class="dim">{req_h[1].lower()}</span>
<span class="hl">{req_body}</span>

<span class="p">$</span> <b style="color:#e6edf3">curl -i -H "X-PAYMENT: &lt;base64 payment&gt;"</b> "http://localhost:8793/v1/readings?sensor=noise&amp;limit=2"
{res_h[0].replace('HTTP/1.1 200 OK', '<span class="s200">HTTP/1.1 200 OK</span>')}
<span class="dim">x-payment-response: eyJzdWNjZXNzIjp0cnVlLCJuZXR3b3JrIjoiYmFzZSIsInNldHRsZW1lbnQiOiJtb2NrLWRldiIsInRyYW5zYWN0aW9uIjoiMHhtb2NrMWEwN2VmZmU4MDEiLCJwYXllciI6IjB4bW9ja3BheWVyIn0=</span>
<span class="hl">{res_body}</span>
</body></html>"""

TREE = """sensormesh/
├── LICENSE
├── README.md                  architecture, quickstart, x402 flow
├── artifacts/
│   ├── sensormesh-shots/      Devpost screenshots (7)
│   └── shoot.py               screenshot harness
├── dashboard/
│   ├── index.html             x402 client demo + charts
│   └── readings.jsonl
├── data/
│   ├── sensormesh-sample.csv
│   └── sensormesh-sample.jsonl
├── docs/
│   ├── video-script.md        90s Devpost video, 8 shots
│   └── x402-metered-access.md API + pricing design
├── mcp/
│   ├── api.js                 x402 HTTP API (express, :8793)
│   ├── index.js               MCP server (stdio)
│   ├── lib/query.js           shared query engine
│   └── package.json
├── simulator/simulate.py      seeded device simulator (stdlib only)
└── state/                     day reports
"""

def term_page(page, title, body_html, w, h):
    page.set_content(f"""<!doctype html><html><head><meta charset="utf-8"><style>
    body {{ margin:0; background:#11151c; display:flex; align-items:center; justify-content:center; }}
    .term {{ background:#0a0e13; border:1px solid #30363d; border-radius:10px; overflow:hidden; box-shadow:0 12px 40px rgba(0,0,0,.5); width:{w-80}px; }}
    .bar {{ display:flex; align-items:center; gap:6px; padding:8px 12px; background:#10151c; border-bottom:1px solid #21262d; }}
    .t {{ width:10px; height:10px; border-radius:50%; }}
    .bar .t:nth-child(1) {{ background:#f85149 }} .bar .t:nth-child(2) {{ background:#d29922 }} .bar .t:nth-child(3) {{ background:#3fb950 }}
    .ttl {{ margin-left:8px; color:#8b949e; font:11px ui-monospace,Menlo,monospace; }}
    pre {{ margin:0; padding:16px 18px; font:12.5px/1.65 ui-monospace,Menlo,Consolas,monospace; color:#c9d1d9; white-space:pre-wrap; word-break:break-all; }}
    {body_html[0]}
    </style></head><body><div class="term"><div class="bar"><span class="t"></span><span class="t"></span><span class="t"></span><span class="ttl">{title}</span></div><pre>{body_html[1]}</pre></div></body></html>""")

with sync_playwright() as p:
    b = p.chromium.launch()

    # 06 — curl 402/200
    pg = b.new_page(viewport={"width": 1040, "height": 700}, device_scale_factor=2)
    style = ".p{color:#7ee787}.s402{color:#d29922;font-weight:700}.s200{color:#3fb950;font-weight:700}.dim{color:#6e7681}.hl{color:#a5d6ff}b{color:#e6edf3}"
    body = f"""<span class="p">$</span> <b>curl -i</b> "http://localhost:8793/v1/readings?sensor=noise&amp;limit=2"
<span class="s402">{req_h[0]}</span>
<span class="dim">{req_h[1].lower()}</span>
<span class="hl">{req_body}</span>

<span class="p">$</span> <b>curl -i -H "X-PAYMENT: &lt;base64 payment&gt;"</b> "http://localhost:8793/v1/readings?sensor=noise&amp;limit=2"
<span class="s200">{res_h[0]}</span>
<span class="dim">{res_h[1].lower()}</span>
<span class="hl">{res_body}</span>"""
    term_page(pg, "x402 round trip — live API, mock settlement (dev)", (style, body), 1040, 700)
    pg.wait_for_timeout(300)
    pg.screenshot(path=f"{OUT}/06-curl-402-200.png")
    print("saved 06")

    # 07 — repo tree
    pg2 = b.new_page(viewport={"width": 980, "height": 620}, device_scale_factor=2)
    style2 = ".c{color:#e6edf3}.cm{color:#8b949e}.p{color:#7ee787}"
    tlines = []
    for l in TREE.rstrip().split("\n"):
        if "←" in l or "#" in l and "  " in l:
            name, _, cm = l.partition("  ")
            tlines.append(f'<span class="c">{name}</span><span class="cm">  {cm.strip()}</span>')
        else:
            tlines.append(f'<span class="c">{l}</span>')
    body2 = f'<span class="cm"># github.com/jayjex/sensormesh — MIT</span>\n' + "\n".join(tlines)
    term_page(pg2, "repo tree", (style2, body2), 980, 620)
    pg2.wait_for_timeout(300)
    pg2.screenshot(path=f"{OUT}/07-repo-tree.png")
    print("saved 07")
    b.close()
