"use strict";

const express = require("express");

const app = express();
app.use(express.json());

const SIDECAR_URL = (process.env.KEPRIX_SIDECAR_URL || "http://127.0.0.1:3360").replace(/\/$/, "");
const PROJECT_KEY = process.env.KEPRIX_PROJECT_KEY || "express_demo";
const DEMO_TOKEN = process.env.DEMO_TOKEN || "";
const PORT = Number(process.env.PORT || 8098);

const ORDERS = {
  ord_1001: {
    id: "ord_1001",
    status: "paid",
    total: 42.5,
    currency: "GBP",
    created_at: "2026-08-01T10:00:00Z",
  },
};

function authHeaders(extraBearer) {
  const token = extraBearer || DEMO_TOKEN;
  if (!token) {
    throw new Error("DEMO_TOKEN not set");
  }
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
    "X-Correlation-Id": "express-starter",
  };
}

app.get("/health", (_req, res) => {
  res.json({ status: "ok", project: PROJECT_KEY });
});

app.get("/api/orders/:id", (req, res) => {
  const order = ORDERS[req.params.id];
  if (!order) return res.status(404).json({ error: "order not found" });
  return res.json(order);
});

app.get("/api/keprix/v1/health", (_req, res) => {
  res.json({ status: "ok" });
});

app.post("/api/keprix/v1/events/ack", (req, res) => {
  res.json({ acked: true, id: req.body && req.body.id });
});

app.post("/demo/pair", async (req, res) => {
  try {
    const response = await fetch(`${SIDECAR_URL}/sidecar/v1/pair/bootstrap`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        pairing_code: req.body.pairing_code,
        project_key: PROJECT_KEY,
        deployment: req.body.deployment || "local-dev",
        environment: req.body.environment || "local",
      }),
    });
    const text = await response.text();
    res.status(response.status).type("json").send(text || "{}");
  } catch (err) {
    res.status(500).json({ error: String(err.message || err) });
  }
});

app.get("/demo/sidecar-health", async (req, res) => {
  try {
    const auth = req.header("authorization");
    const bearer = auth && auth.toLowerCase().startsWith("bearer ") ? auth.slice(7) : undefined;
    const response = await fetch(
      `${SIDECAR_URL}/sidecar/v1/projects/${PROJECT_KEY}/health`,
      { headers: authHeaders(bearer) },
    );
    const text = await response.text();
    res.status(response.status).type("json").send(text || "{}");
  } catch (err) {
    res.status(500).json({ error: String(err.message || err) });
  }
});

app.post("/demo/invoke", async (req, res) => {
  try {
    const auth = req.header("authorization");
    const bearer = auth && auth.toLowerCase().startsWith("bearer ") ? auth.slice(7) : undefined;
    const response = await fetch(
      `${SIDECAR_URL}/sidecar/v1/projects/${PROJECT_KEY}/invoke`,
      {
        method: "POST",
        headers: authHeaders(bearer),
        body: JSON.stringify({
          node: req.body.node || "summarise",
          input: req.body.input || {},
          purpose: req.body.purpose || "demo-summarise",
        }),
      },
    );
    const text = await response.text();
    res.status(response.status).type("json").send(text || "{}");
  } catch (err) {
    res.status(500).json({ error: String(err.message || err) });
  }
});

app.listen(PORT, "127.0.0.1", () => {
  console.log(`express starter listening on http://127.0.0.1:${PORT}`);
});
