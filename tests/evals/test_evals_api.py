"""Eval API route tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app


@pytest.mark.asyncio
async def test_list_eval_suites():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/evals/suites")
    assert response.status_code == 200
    suites = response.json()["suites"]
    assert "chat_basics" in suites
    assert "safety_blocks" in suites
    assert "agent_apps_basics" in suites


@pytest.mark.asyncio
async def test_run_agent_apps_eval_suite():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/evals/run/agent_apps_basics")
    assert response.status_code == 200
    payload = response.json()
    assert payload["suite"] == "agent_apps_basics"
    assert payload["pass_rate"] == 1.0


@pytest.mark.asyncio
async def test_run_eval_suite_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/evals/run/safety_blocks")
    assert response.status_code == 200
    payload = response.json()
    assert payload["suite"] == "safety_blocks"
    assert payload["pass_rate"] == 1.0


@pytest.mark.asyncio
async def test_compare_providers_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/evals/compare",
            json={
                "providers": {
                    "openai": {"pass_rate": 0.9, "avg_cost_usd": 0.03, "avg_latency_ms": 900},
                    "local": {"pass_rate": 0.8, "avg_cost_usd": 0.0, "avg_latency_ms": 1200},
                }
            },
        )
    assert response.status_code == 200
    ranking = response.json()["ranking"]
    assert ranking[0]["provider"] == "openai"
    assert ranking[0]["rank"] == 1
