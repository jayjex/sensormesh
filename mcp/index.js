#!/usr/bin/env node
/**
 * sensormesh-mcp: MCP server over the SensorMesh sensor data commons.
 *
 * Architecture follows dataset-mcp v1.1.1 (github.com/jayjex/dataset-mcp):
 * load the released file once, pin it to its SHA-256, answer queries from memory.
 * Here the data ships in the repo (data/sensormesh-sample.csv), so there is no
 * download step; the hash still proves which file you are querying.
 *
 * Tools:
 *  - list_sensors()                    : devices, sites, sensor types, time range, row counts
 *  - query_readings({...})             : filter + paginate readings (100 rows/call)
 *  - get_stats({sensor?})              : per-sensor min/mean/max, anomaly counts
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const VERSION = "0.1.0";
const HERE = dirname(fileURLToPath(import.meta.url));
const DATA_PATH =
  process.env.SENSORMESH_DATA_PATH || join(HERE, "..", "data", "sensormesh-sample.csv");
const MAX_ROWS_PER_CALL = 100;
const DEFAULT_ROWS_PER_CALL = 20;

// ---------------------------------------------------------------- data loading

let loaded = null; // { sha256, rows, header }

async function loadData() {
  if (loaded) return loaded;
  const text = await readFile(DATA_PATH, "utf8");
  const lines = text.trim().split("\n");
  const header = lines[0].split(",");
  const rows = lines.slice(1).map((line) => {
    const cells = line.split(",");
    const r = {};
    header.forEach((c, i) => (r[c] = cells[i]));
    r.value = Number(r.value);
    return r;
  });
  loaded = { sha256: createHash("sha256").update(text).digest("hex"), rows, header };
  return loaded;
}

function matches(r, f) {
  if (f.device && r.device_id !== f.device) return false;
  if (f.site && r.site !== f.site) return false;
  if (f.sensor && r.sensor_type !== f.sensor) return false;
  if (f.anomaly && r.anomaly !== f.anomaly) return false;
  if (f.since && r.timestamp < f.since) return false;
  if (f.until && r.timestamp > f.until) return false;
  return true;
}

const esc = (v) => {
  const s = v === null || v === undefined ? "" : String(v);
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

const server = new McpServer({
  name: "sensormesh-mcp",
  version: VERSION,
});

server.tool(
  "list_sensors",
  "List the SensorMesh sensor data commons: devices, sites, sensor types, time coverage, row counts. Call this before query_readings to see what exists.",
  {},
  async () => {
    const { rows, sha256 } = await loadData();
    const devices = {};
    for (const r of rows) {
      devices[r.device_id] ??= { site: r.site, sensors: new Set(), rows: 0 };
      devices[r.device_id].sensors.add(r.sensor_type);
      devices[r.device_id].rows++;
    }
    const times = rows.map((r) => r.timestamp).sort();
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              data_file: DATA_PATH,
              sha256,
              rows: rows.length,
              time_range: [times[0], times[times.length - 1]],
              sensor_types: [...new Set(rows.map((r) => r.sensor_type))],
              devices: Object.fromEntries(
                Object.entries(devices).map(([id, d]) => [
                  id,
                  { site: d.site, sensor_types: [...d.sensors], readings: d.rows },
                ])
              ),
            },
            null,
            2
          ),
        },
      ],
    };
  }
);

server.tool(
  "query_readings",
  "Filter and paginate sensor readings. Max 100 rows per call; pass next_offset to keep paging. Filters combine with AND. anomaly='' matches normal readings; 'spike', 'stuck', 'flatline', 'passby' are anomaly flags.",
  {
    device: z.string().optional().describe('Device id, e.g. "sm-001". See list_sensors.'),
    site: z
      .enum(["metro-core", "riverside-park", "north-industrial"])
      .optional()
      .describe("Site filter."),
    sensor: z
      .enum(["air_quality", "temperature", "noise"])
      .optional()
      .describe("Sensor type filter."),
    anomaly: z
      .string()
      .optional()
      .describe('Exact anomaly flag: "" for clean readings, or "spike", "stuck", "flatline", "passby".'),
    since: z.string().optional().describe("ISO timestamp, inclusive lower bound on timestamp."),
    until: z.string().optional().describe("ISO timestamp, inclusive upper bound on timestamp."),
    limit: z.number().int().min(1).optional().default(DEFAULT_ROWS_PER_CALL)
      .describe(`Rows to return per call, capped at ${MAX_ROWS_PER_CALL}.`),
    offset: z.number().int().min(0).optional().default(0).describe("Row offset into the filtered result set."),
    format: z.enum(["json", "csv"]).optional().default("json").describe("json returns objects; csv returns the page as CSV text."),
  },
  async ({ device, site, sensor, anomaly, since, until, limit, offset, format }) => {
    const { rows, sha256, header } = await loadData();
    const f = { device, site, sensor, anomaly, since, until };
    const filtered = rows.filter((r) => matches(r, f));
    const capped = Math.min(limit, MAX_ROWS_PER_CALL);
    const page = filtered.slice(offset, offset + capped);
    const nextOffset = offset + capped < filtered.length ? offset + capped : null;
    const base = {
      data_file: DATA_PATH,
      sha256,
      total_rows_in_file: rows.length,
      total_matched: filtered.length,
      offset,
      returned: page.length,
      next_offset: nextOffset,
    };
    if (format === "csv") {
      const cols = header;
      const csvText =
        cols.map(esc).join(",") +
        "\n" +
        page.map((r) => cols.map((c) => esc(r[c])).join(",")).join("\n");
      return {
        content: [{ type: "text", text: JSON.stringify({ ...base, format: "csv", csv: csvText }, null, 2) }],
      };
    }
    return {
      content: [{ type: "text", text: JSON.stringify({ ...base, format: "json", rows: page }, null, 2) }],
    };
  }
);

server.tool(
  "get_stats",
  "Summary statistics per sensor type: reading count, min, mean, max, and how many readings carry each anomaly flag. Pass sensor to scope to one type.",
  {
    sensor: z.enum(["air_quality", "temperature", "noise"]).optional().describe("Scope stats to one sensor type."),
    device: z.string().optional().describe('Scope stats to one device id, e.g. "sm-001".'),
  },
  async ({ sensor, device }) => {
    const { rows } = await loadData();
    const subset = rows.filter(
      (r) => (!sensor || r.sensor_type === sensor) && (!device || r.device_id === device)
    );
    const groups = {};
    for (const r of subset) {
      const g = (groups[r.sensor_type] ??= { n: 0, min: Infinity, max: -Infinity, sum: 0, flags: {} });
      g.n++;
      g.min = Math.min(g.min, r.value);
      g.max = Math.max(g.max, r.value);
      g.sum += r.value;
      if (r.anomaly) g.flags[r.anomaly] = (g.flags[r.anomaly] || 0) + 1;
    }
    const stats = Object.fromEntries(
      Object.entries(groups).map(([t, g]) => [
        t,
        { readings: g.n, min: g.min, mean: Math.round((g.sum / g.n) * 100) / 100, max: g.max, anomaly_flags: g.flags },
      ])
    );
    return {
      content: [{ type: "text", text: JSON.stringify({ scope: { sensor, device }, stats }, null, 2) }],
    };
  }
);

await server.connect(new StdioServerTransport());
