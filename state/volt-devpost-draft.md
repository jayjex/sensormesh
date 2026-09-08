# SensorMesh — Devpost submission copy (draft, day 4)

Fill these into the Devpost form. Parent review before submit. ~300-word description below.

## Project name

SensorMesh

## Tagline

The street's data, without the login.

## Description (~300 words)

Cities deploy air quality sensors at street level, then keep the readings behind accounts and 48-hour export queues. The data was collected in public. Getting it shouldn't take two days.

SensorMesh is an open sensor-data commons for city environmental readings. One command generates a full day of realistic readings: 1,296 rows, 9 devices, 3 sites, deterministic with a seed. The file is the API: it ships in the repo, pinned to its SHA-256, and every query response reports the hash it came from.

Three access tiers back the same data file. Raw files: free, in the repo. MCP: free, any LLM session (`list_sensors`, `query_readings`, `get_stats` with filters, pagination, and anomaly flags). Metered HTTP: $0.001 per call over x402, USDC on Base, for apps that want an endpoint instead of a download.

The dashboard doubles as an x402 client. Click "Buy API access" and watch the round trip: the unpaid call returns a 402 with the price, a mock wallet signs the payment, the retry returns the data plus a settlement receipt. A terminal pane prints the same exchange as it happens.

Architecture: one shared query engine (`mcp/lib/query.js`) backs both MCP and HTTP, so the free path and the paid path stay consistent by construction. A vanilla-JS dashboard needs no build step.

Honest scope: this is the dev build. On-chain verification and settlement run through a facilitator in production; here they are mocked behind two seam functions (`verifyPayment` / `settlePayment`) documented in `docs/x402-metered-access.md`. Swap in a real facilitator and funded Base wallet and the same routes settle on-chain. No other code changes.

The data is simulated for now. The schema is the deliverable: real devices can publish it unchanged.

## Judging criteria alignment

- **Innovation** — sha256 pinning on every query response; x402 per-call payments on an open data commons (usually these are free-forever downloads or walled portals); the schema doubles as a payment boundary.
- **Complexity** — device simulator with diurnal curves, drift, and anomaly injection; shared query engine under two transports (MCP stdio, express HTTP); browser x402 client signing `exact`-scheme payments; mock-facilitator seam so the whole payment path is testable with curl.
- **Impact** — gives researchers a path around login walls and export queues; gives cities an open publishing schema; gives app developers metered, paid access instead of bulk scraping.
- **Design** — dashboard shows live charts, per-sensor tier badges, and the payment flow step-by-step (402 in amber, 200 in green, settlement receipt pills) with the real request/response printed alongside.
- **Presentation** — 99-second screen-recorded walkthrough (`artifacts/video/sensormesh-demo.mp4`, script targeted 90s and shot 5 gets the extra seconds), 8-slide deck (`artifacts/deck/`), 7 screenshots. Every number on screen comes from the repo; the mock settlement is labeled on screen.

## Other form fields

- **Screenshots** — `artifacts/sensormesh-shots/01..07` (day 3 set).
- **Video/presentation** — upload `artifacts/video/sensormesh-demo.mp4` (99s, 1600×900) and/or the deck `artifacts/deck/` as PDF/PNG.
- **Repo** — https://github.com/jayjex/sensormesh (MIT).
- **Built with** — Node.js, express, x402 (exact scheme), MCP, Chart.js, vanilla JS, Python (stdlib-only simulator).

## Slop check (run 1 — self, before commit)

Checked against the no-ai-slop skill: no banned words (delve/foster/leverage/robust/empower/elevate...), no "not X but Y" contrasts, no throat-clearing openers, no importance puffery, no colon reveals, no weasel attribution, no fake-profound kicker (closing line is a plain fact). Concrete numbers throughout (1,296 rows, 9 devices, 3 sites, $0.001, 48 hours). Active voice. PASS.

## Slop check (run 2 — after re-read)

Re-read the full draft end to end. Cut em dashes down to zero in the description (list colons and periods carry the same weight). Checked the closing line isn't a metaphor — it's the scope statement. Verified naming matches the repo ("x402 client", "exact scheme", seam function names). PASS.
