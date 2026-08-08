"""FastAPI starter for Keprix Universal Sidecar (demo only)."""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Keprix Universal Sidecar FastAPI starter")

SIDECAR_URL = os.environ.get("KEPRIX_SIDECAR_URL", "http://127.0.0.1:3360").rstrip("/")
PROJECT_KEY = os.environ.get("KEPRIX_PROJECT_KEY", "fastapi_demo")
DEMO_TOKEN = os.environ.get("DEMO_TOKEN", "")

ORDERS = {
    "ord_1001": {
        "id": "ord_1001",
        "status": "paid",
        "total": 42.50,
        "currency": "GBP",
        "created_at": "2026-08-01T10:00:00Z",
    }
}


class PairBody(BaseModel):
    pairing_code: str
    deployment: str = "local-dev"
    environment: str = "local"


class InvokeBody(BaseModel):
    node: str = "summarise"
    input: dict[str, Any] = {}
    purpose: str = "demo-summarise"


def _auth_headers(bearer: str | None = None) -> dict[str, str]:
    token = bearer or DEMO_TOKEN
    if not token:
        raise HTTPException(status_code=500, detail="DEMO_TOKEN not set")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Correlation-Id": "fastapi-starter",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "project": PROJECT_KEY}


@app.get("/api/orders/{order_id}")
def get_order(order_id: str) -> dict[str, Any]:
    order = ORDERS.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order not found")
    return order


@app.get("/api/keprix/v1/health")
def keprix_health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/keprix/v1/events/ack")
def events_ack(payload: dict[str, Any]) -> dict[str, Any]:
    return {"acked": True, "id": payload.get("id")}


@app.post("/demo/pair")
async def pair(body: PairBody) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{SIDECAR_URL}/sidecar/v1/pair/bootstrap",
            headers=_auth_headers(),
            json={
                "pairing_code": body.pairing_code,
                "project_key": PROJECT_KEY,
                "deployment": body.deployment,
                "environment": body.environment,
            },
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


@app.get("/demo/sidecar-health")
async def sidecar_health(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    bearer = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", 1)[1]
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{SIDECAR_URL}/sidecar/v1/projects/{PROJECT_KEY}/health",
            headers=_auth_headers(bearer),
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


@app.post("/demo/invoke")
async def invoke(
    body: InvokeBody,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    bearer = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", 1)[1]
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{SIDECAR_URL}/sidecar/v1/projects/{PROJECT_KEY}/invoke",
            headers=_auth_headers(bearer),
            json={
                "node": body.node,
                "input": body.input,
                "purpose": body.purpose,
            },
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()
