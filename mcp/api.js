#!/usr/bin/env node
/**
 * sensormesh-api: metered HTTP API over the SensorMesh commons (x402).
 *
 * Implements docs/x402-metered-access.md: same query engine as the MCP server
 * (lib/query.js), priced per call over x402 (exact scheme, USDC on Base).
 *
 * Endpoints:
 *   GET /v1/sensors   free   device/site/sensor inventory
 *   GET /v1/stats     free   per-sensor min/mean/max + anomaly counts
 *   GET /v1/preview   free   first 10 rows of any filtered query
 *   GET /v1/readings  $0.001 per call, x402 exact scheme
 *
 * x402 flow (protocol draft 0.2):
 *   1. Client calls GET /v1/readings.
 *   2. No payment header -> 402 with X-PAYMENT (base64 JSON payment requirements)
 *      and an `accepts` array in the body.
 *   3. Client pays and retries with X-PAYMENT (base64 JSON payment payload).
 *   4. Server verifies + settles, returns data with X-PAYMENT-RESPONSE.
 *
 * Dev build: on-chain verification/settlement runs through a facilitator in
 * production. This server ships with SENSORMESH_MOCK_SETTLEMENT=1, which
 * verifies the X-PAYMENT payload shape locally and settles with a mock
 * transaction id, so the full 402 -> pay -> 200 round trip is testable with
 * curl. Real settlement plugs in at the same two seam functions
 * (verifyPayment / settlePayment).
 */
import express from "express";
import {
  DATA_PATH,
  DEFAULT_ROWS_PER_CALL,
  MAX_ROWS_PER_CALL,
  SITES,
  SENSOR_TYPES,
  listSensors,
  queryReadings,
  pageToCsv,
  getStats,
} from "./lib/query.js";

const PORT = Number(process.env.PORT || 8793);
const VERSION = "0.1.0";
const PRICE_USD = "$0.001";
const MAX_AMOUNT_REQUIRED = "1000"; // USDC, 6 decimals
const PAY_TO = process.env.SENSORMESH_PAY_TO || "0x00000000000000000000000000000000000dead0";
const ASSET = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"; // USDC (Base)
const NETWORK = "base";
const X402_VERSION = 1;
const MOCK_SETTLEMENT = process.env.SENSORMESH_MOCK_SETTLEMENT === "1";

const paymentRequirements = (resource) => ({
  x402Version: X402_VERSION,
  scheme: "exact",
  network: NETWORK,
  asset: ASSET,
  payTo: PAY_TO,
  maxAmountRequired: MAX_AMOUNT_REQUIRED,
  resource,
  description: `SensorMesh readings query (${PRICE_USD} per call)`,
  mimeType: "application/json",
  maxTimeoutSeconds: 30,
});

// ------------------------------------------------------- payment seam (x402)

/** Verify a client X-PAYMENT payload against the payment requirements. */
function verifyPayment(payment, requirements) {
  if (!payment || payment.x402Version !== X402_VERSION) return "unsupported x402 version";
  if (payment.scheme !== "exact") return "unsupported scheme";
  if (payment.resource !== requirements.resource) return "payment resource mismatch";
  if (MOCK_SETTLEMENT) return null; // dev: shape checked, amount honored at settle
  return "facilitator not configured"; // production: call facilitator.verify here
}

/** Settle after verification. Returns X-PAYMENT-RESPONSE payload. */
async function settlePayment(payment, requirements) {
  if (MOCK_SETTLEMENT) {
    const payload = payment.payload || {};
    return {
      success: true,
      network: NETWORK,
      settlement: "mock-dev",
      transaction: `0xmock${Date.now().toString(16)}`,
      payer: payload.from || "0xmockpayer",
    };
  }
  throw new Error("facilitator not configured"); // production: call facilitator.settle here
}

const b64 = (o) => Buffer.from(JSON.stringify(o)).toString("base64");
const unb64 = (s) => {
  try {
    return JSON.parse(Buffer.from(s, "base64").toString("utf8"));
  } catch {
    return null;
  }
};

// ------------------------------------------------------------------- routes

const app = express();
app.disable("x-powered-by");
app.use((req, res, next) => {
  res.set("Access-Control-Allow-Origin", "*");
  res.set("Access-Control-Expose-Headers", "X-PAYMENT, X-PAYMENT-RESPONSE");
  next();
});

// Parse filters off the query string with the same enums as the MCP tool.
function filtersFromQuery(q) {
  const f = {};
  if (q.device) f.device = String(q.device);
  if (q.site && SITES.includes(q.site)) f.site = q.site;
  if (q.sensor && SENSOR_TYPES.includes(q.sensor)) f.sensor = q.sensor;
  if (q.anomaly !== undefined) f.anomaly = String(q.anomaly);
  if (q.since) f.since = String(q.since);
  if (q.until) f.until = String(q.until);
  return f;
}

function meta(req, out) {
  const { header, page, ...base } = out;
  return {
    ...base,
    endpoint: req.path,
    filters: filtersFromQuery(req.query),
  };
}

for (const base of ["/v1", ""]) {
  app.get(`${base}/sensors`, async (req, res) => {
    res.json(await listSensors());
  });

  app.get(`${base}/stats`, async (req, res) => {
    res.json(await getStats(filtersFromQuery(req.query)));
  });

  // Free sample: first 10 rows of any filtered query.
  app.get(`${base}/preview`, async (req, res) => {
    const out = await queryReadings(filtersFromQuery(req.query), 10, 0);
    if (req.query.format === "csv") {
      res.type("text/csv").send(pageToCsv(out.page, out.header));
      return;
    }
    res.json({ ...meta(req, out), rows: out.page, format: "json", free_preview: 10 });
  });

  // Metered: $0.001 per call over x402.
  app.get(`${base}/readings`, async (req, res) => {
    const resource = `${req.baseUrl || "/v1"}/readings`;
    const requirements = paymentRequirements(resource);
    const header = req.get("X-PAYMENT");

    if (!header) {
      const body = {
        x402Version: X402_VERSION,
        error: "X-PAYMENT header is required",
        accepts: [requirements],
      };
      res.set("X-PAYMENT", b64(requirements));
      res.status(402).json(body);
      return;
    }

    const payment = unb64(header);
    const verifyError = verifyPayment(payment, requirements);
    if (verifyError) {
      res.set("X-PAYMENT", b64(requirements));
      res.status(402).json({ x402Version: X402_VERSION, error: verifyError, accepts: [requirements] });
      return;
    }

    try {
      const settlement = await settlePayment(payment, requirements);
      const limit = Math.min(Number(req.query.limit) || DEFAULT_ROWS_PER_CALL, MAX_ROWS_PER_CALL);
      const offset = Math.max(Number(req.query.offset) || 0, 0);
      const out = await queryReadings(filtersFromQuery(req.query), limit, offset);
      if (req.query.format === "csv") {
        res.set("X-PAYMENT-RESPONSE", b64(settlement));
        res.type("text/csv").send(pageToCsv(out.page, out.header));
        return;
      }
      res.set("X-PAYMENT-RESPONSE", b64(settlement));
      res.json({ ...meta(req, out), rows: out.page, format: "json", settlement });
    } catch (err) {
      res.status(500).json({ error: String(err.message || err) });
    }
  });
}

app.get("/health", async (req, res) => {
  const { total_rows_in_file, sha256 } = await queryReadings({}, 1, 0);
  res.json({ ok: true, version: VERSION, mock_settlement: MOCK_SETTLEMENT, rows: total_rows_in_file, sha256, data_file: DATA_PATH });
});

app.listen(PORT, "127.0.0.1", () => {
  console.log(`[sensormesh-api] :${PORT} payTo=${PAY_TO} price=${PRICE_USD} mock_settlement=${MOCK_SETTLEMENT}`);
});
