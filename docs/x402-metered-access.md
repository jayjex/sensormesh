# Metered sensor access over x402 — design

Day 2 build status: **live**. Shared query engine (`mcp/lib/query.js`) backs the
MCP tools and the HTTP API (`mcp/api.js`, systemd `sensormesh-api`, port 8793,
public via cloudflared quick tunnel — see `mcp/public-url.txt`).
`SENSORMESH_MOCK_SETTLEMENT=1` verifies the X-PAYMENT payload shape and settles
with a mock transaction id, so the full 402 → pay → 200 round trip runs today;
real settlement plugs into the `verifyPayment` / `settlePayment` seams.

The rest of this doc is the original design (and still the production plan):

## Access tiers

| tier | surface | price | who |
|---|---|---|---|
| raw files | this repo, `data/` | free | everyone |
| MCP | `@jayjex/sensormesh-mcp` | free | LLM sessions, humans exploring |
| metered HTTP | x402-gated API | per call | production apps |

The first two ship in the day 1 build (done). The third is live in dev mode
(mock settlement) since day 2; production settlement needs a facilitator and a
real `payTo` wallet.

## Why per-call fits sensor data

Static datasets are one download. Sensor data is a stream: an app that checks noise levels near a venue wants last night's readings, not last year's archive. Per-call metering prices the query, not the pipeline. The x402 flow means the caller pays from a wallet with no account signup, and the seller runs no billing stack.

## Endpoint plan

`GET /v1/readings` with the same filters as the MCP tool:

| param | meaning |
|---|---|
| `device`, `site`, `sensor` | scoping (same enums as `query_readings`) |
| `since`, `until` | time window |
| `anomaly` | flag filter, empty = clean only |
| `limit` | rows per call, cap 100 |

Pricing: free up to 100 rows/call while the demo runs, then $0.001 per call after the meter turns on. A free `GET /v1/preview` (10 rows) keeps the sample-free / full-query split from dataset-mcp.

## x402 flow (protocol draft 0.2, Base network, USDC)

1. Client calls `GET /v1/readings?...`.
2. No payment header: server answers `402 Payment Required` with `X-PAYMENT` (base64 JSON: scheme, asset, payTo, maxAmountRequired, resource).
3. Client pays (x402-fetch / mpp client handles this in one line) and retries with `X-PAYMENT`.
4. Server verifies + settles payment, returns data with `X-PAYMENT-RESPONSE`.

Sketch (express, `x402-express` middleware):

```js
import { paymentMiddleware, exact } from "x402-express";

app.use(paymentMiddleware(
  "0xPAYTO",
  { "/v1/readings": { price: "$0.001", network: "base" } },
  { facilitatorUrl: "https://facilitator.x402.org" }  // testnet while hacking
));

app.get("/v1/readings", (req, res) => {
  // filters already validated; serve from the in-memory store the MCP server uses
  res.json(serve(req.query));
});
```

## Reuse

The query engine (filters, pagination, hash pinning) lives once and backs both surfaces: MCP tool handlers call the same functions the HTTP route calls. That keeps MCP (free exploration) and HTTP (metered production) consistent by construction, same as the dataset-mcp free-sample / full-query split.
