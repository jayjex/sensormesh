# SensorMesh — 90-second video script (draft, day 3)

Target: Devpost submission video, ~90s, 8 shots.
Rules this script follows: every number on screen comes from the repo (seed 42 sample or live API output); settlement is labeled "mock settlement (dev)"; no claims the build can't back. Real facilitator + funded wallet is the only thing not shown, and the script says so.

| # | time | screen | voiceover |
|---|---|---|---|
| 1 | 0:00–0:10 | A city open-data portal: login wall, "export request will be processed in 48 hours" | Cities deploy air quality sensors, then lock the readings behind a login. Researchers file records requests for data that should be public. |
| 2 | 0:10–0:20 | Terminal: `python3 simulator/simulate.py --seed 42` writes 1,296 rows, 9 devices, 3 sites | SensorMesh is the other side. Devices publish to an open catalog with stable schemas. This repo runs today: one command regenerates a full day of readings, same seed, same data. |
| 3 | 0:20–0:30 | Terminal: `query_readings({ site: "riverside-park", sensor: "noise", anomaly: "spike" })` returns rows + sha256 | Any LLM session queries the mesh over MCP. Filter by site, sensor, time range, anomaly flag. Every response pins the sha256 of the data file it came from. |
| 4 | 0:30–0:40 | Dashboard: time series, per-site means, anomaly counts | The dashboard reads the same file. Time series, per-site means, anomaly counts, CSV export of whatever filter you set. |
| 5 | 0:40–1:00 | Dashboard → "Buy API access" click: step 1 lights up `402`, step 2 signs, step 3 `200`; terminal pane shows the same round trip | Metered HTTP access runs over x402. The unpaid call gets a 402 with the price: a tenth of a cent per call, USDC on Base. The client signs, retries with the payment header, and gets the data plus a settlement receipt. This is the dev build, so settlement is mocked. Watch the terminal: 402, pay, 200. |
| 6 | 1:00–1:12 | ASCII architecture diagram (README): simulator → data files → query.js → MCP + HTTP, x402 seams marked | One query engine backs MCP and HTTP, so the free path and the paid path stay consistent by construction. Mock settlement is a seam: swap in a real facilitator and the same routes settle on-chain. |
| 7 | 1:12–1:24 | The three access tiers as overlay text over the dashboard | Three tiers. Raw files: free, in the repo. MCP: free, any LLM. Metered HTTP: per-call pricing for apps that want an endpoint instead of a download. The data is simulated for now. The schema is the deliverable, and real devices can publish it unchanged. |
| 8 | 1:24–1:30 | Repo card: github.com/jayjex/sensormesh, MIT license | Clone it, run it, query it. SensorMesh: the street's data, without the login. |

## Production notes

- Shots 2, 3, 5 are screen recordings of the real thing (simulator output, live MCP query, live x402 round trip on 127.0.0.1:8793). No mockups.
- Keep the `mock settlement (dev)` pill visible in shot 5. Judges should never wonder whether the payment is real.
- Shot 1: record the login wall from a real public portal, or a plain text slide. Don't fabricate a screenshot of a named vendor.
- If the video runs short, let the shot 5 terminal round trip breathe an extra 2 seconds; it's the money shot.
