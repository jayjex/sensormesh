# VoltHacks day 2 report — 2026-09-08 (repo @ 85a7cfe)

Goal: shared query engine + x402 HTTP API live. Both done, E2E tested.

## Shipped

1. **Shared query engine** — `mcp/lib/query.js`. Filters, pagination, CSV render, stats, SHA-256 pinning. `mcp/index.js` (MCP) and `mcp/api.js` (HTTP) both call it, so MCP and HTTP stay consistent by construction (per `docs/x402-metered-access.md`). Also fixed a day-1 bug: CSV rows kept a trailing `\r` (CRLF parse), which broke the `anomaly` filter.
2. **x402 HTTP API** — `mcp/api.js`, express 5, port 8793, bound to 127.0.0.1:
   - `GET /v1/sensors` free — inventory
   - `GET /v1/stats` free — min/mean/max + anomaly counts
   - `GET /v1/preview` free — 10 rows of any filtered query
   - `GET /v1/readings` $0.001/call — x402 `exact` scheme, USDC on Base (`maxAmountRequired` 1000 base units), requirements in `X-PAYMENT` header + body `accepts`, settlement proof in `X-PAYMENT-RESPONSE`
   - `GET /health` free
   - Dev mode `SENSORMESH_MOCK_SETTLEMENT=1`: verifies payment payload shape (x402Version, scheme, resource match), settles with mock tx id. Real facilitator plugs into the `verifyPayment` / `settlePayment` seams without touching routes.
3. **Deploy** — standalone systemd user units `sensormesh-api.service` (origin) + `sensormesh-tunnel.service` (own cloudflared quick tunnel, URL harvested to `mcp/public-url.txt`). apimarket/x402-rest/fiatdock units untouched, no restarts. Tunnel outlives origin restarts (no Requires/BindTo), same pattern as apimarket-tunnel.

## E2E (local + through tunnel)

| case | result |
|---|---|
| no payment header | 402 + requirements JSON (scheme/base/USDC/payTo/max) |
| paid retry (mock settlement) | 200 + data + `X-PAYMENT-RESPONSE` (`success`, mock tx, payer) |
| garbage base64 header | 402 `unsupported x402 version` |
| wrong scheme | 402 `unsupported scheme` |
| resource mismatch | 402 `payment resource mismatch` |
| paid CSV path | 200, CSV with `anomaly=spike` filter applied |
| free preview / stats / sensors | 200 |

MCP smoke test after refactor: `query_readings` + `get_stats` return identical numbers to day 1 (noise spikes: 4 matched, air_quality stats unchanged).

## State

- Pushed: `4cb9d57..85a7cfe` → github.com/jayjex/sensormesh (master).
- Live: origin 127.0.0.1:8793, tunnel `pharmaceuticals-yours-hopefully-mining.trycloudflare.com` (quick tunnels rotate; URL in `mcp/public-url.txt`, gitignored).
- Data: 1,296 rows, 9 devices, 3 sites, sha256 `022b54f9…a1197`.

## Day 3 candidates

- Real facilitator + funded Base testnet wallet → flip off mock settlement.
- Wire dashboard to the HTTP API as an x402 client demo (screenshot fodder for Devpost).
- Video/presentation for submission (deadline Sep 13).
