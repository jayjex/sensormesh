# sensormesh

Open IoT sensor data commons. Every city deploys air quality, temperature, and noise sensors, then locks the readings in a vendor portal behind a login. Researchers grep for CSVs on a portal from 2011, journalists FOIA for what should be public, and app developers give up. The data exists. Nobody can get it out.

SensorMesh flips that. Devices write readings to an open catalog with stable schemas. Anyone can pull the raw files, query them through MCP from any LLM session, or pay per call for metered HTTP access. No account, no vendor portal, no export button that emails you a zip in 48 hours.

**Status: day 3 of the VoltHacks build (Sep 8–13).** Simulator, sample data, MCP server, and dashboard shipped day 1. Day 2 added the shared query engine (`mcp/lib/query.js`) and the metered HTTP API (`mcp/api.js`) with x402 payments, live in dev mode (mock settlement) behind a cloudflared tunnel. Day 3 turned the dashboard into an x402 client: a **Buy API access** button runs the real 402 → sign → 200 round trip in the browser, with per-dataset metered badges. Production facilitator + real wallet land next.

## Architecture

```
simulator/simulate.py --seed 42
        │  writes
        ▼
data/sensormesh-sample.csv + .jsonl
        │
        │  one data file, three consumers
        ├───────────────────────────────► dashboard/index.html (browser)
        │                                         │
        ▼                                         │ fetch
┌───────────────────────────┐                     │
│   mcp/lib/query.js        │                     │
│   filters · pagination    │                     │
│   stats · sha256 pinning  │                     │
└──────┬─────────────┬──────┘                     │
       │             │                            │
┌──────┴──────┐ ┌────┴────────────────────────────▼─────────────┐
│ mcp/index.js│ │ mcp/api.js (express, :8793)                   │
│ MCP over    │ │ /v1/sensors /v1/stats    free                 │
│ stdio       │ │ /v1/preview     10 rows  free                 │
│ list_sensors│ │ /v1/readings            $0.001/call           │
│ query_…     │ │ x402 "exact" scheme · USDC on Base            │
│ get_stats   │ │   verifyPayment() ──► facilitator seam (mock) │
└─────────────┘ │   settlePayment() ──► facilitator seam (mock) │
                └───────────────────────────────────────────────┘
```

The dashboard charts read `readings.jsonl` directly (free path). Its **Buy API access** button is a real x402 client: it fetches the API, decodes the `X-PAYMENT` requirements from the 402, signs a mock payment, retries with the `X-PAYMENT` header, and renders the settlement receipt from `X-PAYMENT-RESPONSE` — the same round trip you'd get with curl or an SDK.

## What's in the box

| piece | what it does | where |
|---|---|---|
| Device simulator | Python, stdlib only. Generates air quality, temperature, and noise readings with 24h curves, drift, and injected anomalies (spike / stuck / flatline / passby). Seeded, so outputs are reproducible. | `simulator/simulate.py` |
| Sample data | 1,296 readings, 9 devices, 3 sites, one full day at 10-minute cadence. CSV + JSONL. | `data/`, `dashboard/readings.jsonl` |
| MCP server | `list_sensors`, `query_readings`, `get_stats`. Filter by device, site, sensor type, time range, anomaly flag. 100 rows per call. | `mcp/index.js` |
| Shared query engine | One implementation of filters, pagination, and hash pinning backing both MCP and HTTP. | `mcp/lib/query.js` |
| HTTP API (x402) | `/v1/sensors` and `/v1/stats` free, `/v1/preview` 10 free rows, `/v1/readings` $0.001 per call over x402 (exact scheme, USDC on Base). | `mcp/api.js` |
| Dashboard | Vanilla JS + Chart.js from CDN. Time series, per-site means, anomaly counts, CSV export of the current filter — plus a built-in x402 client: **Buy API access** runs the 402 → pay → 200 round trip against the API and shows the settlement proof. Per-dataset rows carry `metered $0.001/call` and `MCP free` badges. | `dashboard/index.html` |

## Quick start

Generate a fresh day of readings (writes `data/` CSV + JSONL):

```bash
python3 simulator/simulate.py --days 1 --interval 10 --seed 42
```

Options: `--days`, `--interval` (minutes), `--seed`, `--format csv|jsonl|both`, `--no-anomalies`. Same seed, same data, every time.

Dashboard: open `dashboard/index.html` over any static server (`python3 -m http.server`), it fetches `readings.jsonl` from the same directory.

MCP server (Node 18+):

```bash
cd mcp && npm install
node index.js
```

Add to your MCP client config:

```json
{
  "mcpServers": {
    "sensormesh": {
      "command": "node",
      "args": ["/path/to/sensormesh/mcp/index.js"]
    }
  }
}
```

## Querying the commons

`list_sensors` shows the mesh: devices, sites, time coverage, row counts.

`query_readings` filters and paginates (max 100 rows per call, `next_offset` pages through):

```
query_readings({ site: "riverside-park", sensor: "air_quality", limit: 5 })
```

```json
{
  "total_matched": 144,
  "rows": [
    { "timestamp": "2026-09-08T00:00:00Z", "device_id": "sm-004",
      "site": "riverside-park", "sensor_type": "air_quality", "value": 7.4, "unit": "ug/m3", "anomaly": "" }
  ]
}
```

```
query_readings({ sensor: "noise", anomaly: "spike", limit: 10 })
get_stats({ sensor: "temperature" })
```

The response pins the SHA-256 of the data file, so you always know which release you queried. Same pattern as [dataset-mcp](https://github.com/jayjex/dataset-mcp), applied to streaming sensor data instead of static datasets.

## HTTP API (x402)

Same query engine as MCP, served over HTTP with per-call pricing (design in `docs/x402-metered-access.md`):

| endpoint | price | what it returns |
|---|---|---|
| `GET /v1/sensors` | free | device/site/sensor inventory |
| `GET /v1/stats` | free | per-sensor min/mean/max + anomaly counts |
| `GET /v1/preview` | free | first 10 rows of any filtered query |
| `GET /v1/readings` | $0.001/call | full filtered query, 100 rows max, JSON or CSV |

x402 flow, exactly per protocol draft 0.2: call `/v1/readings` with no header and get `402` with payment requirements in the `X-PAYMENT` header and body; pay (any x402 client); retry with your payment in `X-PAYMENT`; data comes back with settlement proof in `X-PAYMENT-RESPONSE`.

```bash
# 1. price the call
curl -i "$BASE/v1/readings?sensor=noise&limit=5"
# 2. pay with any x402 wallet, then retry:
curl -H "X-PAYMENT: <base64 payment>" "$BASE/v1/readings?sensor=noise&limit=5"
```

Dev mode (`SENSORMESH_MOCK_SETTLEMENT=1`) verifies the payment payload and settles with a mock transaction, so the full round trip runs without a funded wallet. Real settlement plugs into the `verifyPayment` / `settlePayment` seams in `mcp/api.js`.

Run it yourself:

```bash
cd mcp && SENSORMESH_MOCK_SETTLEMENT=1 PORT=8793 node api.js
```

Then open the dashboard and press **Buy API access** — it performs exactly the curl sequence below in the browser, with the payment requirements, signed payload, and settlement receipt rendered at each step.

## Why sensors, why a commons

A weather API tells you what the airport measured. A SensorMesh reading tells you what the street measured: the block that floods, the intersection where PM2.5 triples at school pickup, the park that's 3 degrees cooler than the plaza. That granularity is exactly what urban-health research, city planning, and climate adaptation need, and it's exactly what current deployments hoard.

The commons has three access tiers:

1. **Raw files** — free, in this repo. Generate more with the simulator.
2. **MCP** — free, any LLM session can query the full readings with filters and stats.
3. **Metered HTTP** — per-call pricing over x402, for production apps that want an SLA-shaped endpoint without downloading anything. Live in dev mode with mock settlement; flipping to a real facilitator touches only the two seam functions.

Simulated data keeps the schema honest while real hardware partnerships come together: every consumer of the API (human, LLM, or dashboard) works against the exact shape real devices will publish.

## Data schema

One row per reading:

| column | example | notes |
|---|---|---|
| `timestamp` | `2026-09-08T00:00:00Z` | UTC, ISO 8601 |
| `device_id` | `sm-001` | stable device id |
| `site` | `metro-core` | deployment site: `metro-core`, `riverside-park`, `north-industrial` |
| `sensor_type` | `air_quality` | `air_quality`, `temperature`, `noise` |
| `value` | `23.1` | reading value |
| `unit` | `ug/m3` | `ug/m3` (PM2.5), `C`, `dB` |
| `anomaly` | `spike` | empty for clean readings; `spike`, `stuck`, `flatline`, `passby` otherwise |

## License

MIT.
