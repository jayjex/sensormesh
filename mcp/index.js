#!/usr/bin/env node
/**
 * sensormesh-mcp: MCP server over the SensorMesh sensor data commons.
 *
 * Architecture follows dataset-mcp v1.1.1 (github.com/jayjex/dataset-mcp):
 * load the released file once, pin it to its SHA-256, answer queries from memory.
 * Here the data ships in the repo (data/sensormesh-sample.csv), so there is no
 * download step; the hash still proves which file you are querying.
 *
 * Query logic lives in lib/query.js, shared with the metered HTTP API
 * (api.js, docs/x402-metered-access.md) so both surfaces stay consistent.
 *
 * Tools:
 *  - list_sensors()                    : devices, sites, sensor types, time range, row counts
 *  - query_readings({...})             : filter + paginate readings (100 rows/call)
 *  - get_stats({sensor?})              : per-sensor min/mean/max, anomaly counts
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import {
  DATA_PATH,
  MAX_ROWS_PER_CALL,
  DEFAULT_ROWS_PER_CALL,
  SITES,
  SENSOR_TYPES,
  listSensors,
  queryReadings,
  pageToCsv,
  getStats,
} from "./lib/query.js";

const VERSION = "0.1.0";

const server = new McpServer({
  name: "sensormesh-mcp",
  version: VERSION,
});

server.tool(
  "list_sensors",
  "List the SensorMesh sensor data commons: devices, sites, sensor types, time coverage, row counts. Call this before query_readings to see what exists.",
  {},
  async () => {
    const out = await listSensors();
    return { content: [{ type: "text", text: JSON.stringify(out, null, 2) }] };
  }
);

server.tool(
  "query_readings",
  "Filter and paginate sensor readings. Max 100 rows per call; pass next_offset to keep paging. Filters combine with AND. anomaly='' matches normal readings; 'spike', 'stuck', 'flatline', 'passby' are anomaly flags.",
  {
    device: z.string().optional().describe('Device id, e.g. "sm-001". See list_sensors.'),
    site: z.enum(SITES).optional().describe("Site filter."),
    sensor: z.enum(SENSOR_TYPES).optional().describe("Sensor type filter."),
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
    const out = await queryReadings({ device, site, sensor, anomaly, since, until }, limit, offset);
    const { header, page, ...base } = out;
    if (format === "csv") {
      return {
        content: [{ type: "text", text: JSON.stringify({ ...base, format: "csv", csv: pageToCsv(page, header) }, null, 2) }],
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
    sensor: z.enum(SENSOR_TYPES).optional().describe("Scope stats to one sensor type."),
    device: z.string().optional().describe('Scope stats to one device id, e.g. "sm-001".'),
  },
  async ({ sensor, device }) => {
    const out = await getStats({ sensor, device });
    return { content: [{ type: "text", text: JSON.stringify(out, null, 2) }] };
  }
);

await server.connect(new StdioServerTransport());
