# sensormesh

Open IoT sensor data commons. Every city deploys air quality, temperature, and noise sensors, then locks the readings in a vendor portal behind a login. Researchers grep for CSVs on a portal from 2011, journalists FOIA for what should be public, and app developers give up. The data exists. Nobody can get it out.

SensorMesh flips that. Devices write readings to an open catalog with stable schemas. Anyone can pull the raw files, query them through MCP from any LLM session, or pay per call for metered HTTP access. No account, no vendor portal, no export button that emails you a zip in 48 hours.

**Status: day 1 of the VoltHacks build (Sep 8–13).** Simulator, sample data, MCP server, and dashboard are working. HTTP API with x402 metered access lands next.

## What's in the box

| piece | what it does | where |
|---|---|---|
| Device simulator | Python, stdlib only. Generates air quality, temperature, and noise readings with 24h curves, drift, and injected anomalies (spike / stuck / flatline / passby). Seeded, so outputs are reproducible. | `simulator/simulate.py` |
| Sample data | 1,296 readings, 9 devices, 3 sites, one full day at 10-minute cadence. CSV + JSONL. | `data/`, `dashboard/readings.jsonl` |
| MCP server | `list_sensors`, `query_readings`, `get_stats`. Filter by device, site, sensor type, time range, anomaly flag. 100 rows per call. | `mcp/` |
| Dashboard | Vanilla JS + Chart.js from CDN. Time series, per-site means, anomaly counts, CSV export of the current filter. | `dashboard/index.html` |

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

## Why sensors, why a commons

A weather API tells you what the airport measured. A SensorMesh reading tells you what the street measured: the block that floods, the intersection where PM2.5 triples at school pickup, the park that's 3 degrees cooler than the plaza. That granularity is exactly what urban-health research, city planning, and climate adaptation need, and it's exactly what current deployments hoard.

The commons has three access tiers:

1. **Raw files** — free, in this repo. Generate more with the simulator.
2. **MCP** — free, any LLM session can query the full readings with filters and stats.
3. **Metered HTTP** — per-call pricing over x402, for production apps that want an SLA-shaped endpoint without downloading anything. In progress; lands with the day 3 build.

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
