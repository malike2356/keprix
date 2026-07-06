"""Prompt 14 acceptance tests: local model playbook."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app


@pytest.mark.asyncio
async def test_playbook_scan_linux():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/playbook/scan")
    assert response.status_code == 200
    data = response.json()
    assert "total_ram_gb" in data
    assert "cpu_cores" in data
    assert "platform" in data


@pytest.mark.asyncio
async def test_playbook_models_returns_fit_scores():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/playbook/models")
    assert response.status_code == 200
    data = response.json()
    models = data["models"]
    assert len(models) >= 10
    assert all("fit_score" in m for m in models)
    assert all(0.0 <= m["fit_score"] <= 1.0 for m in models)


@pytest.mark.asyncio
async def test_research_presets():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/playbook/research-presets")
    assert response.status_code == 200
    presets = response.json()
    assert {"small", "medium", "large"} <= set(presets.keys())


@pytest.mark.asyncio
async def test_playbook_benchmark_returns_metrics(monkeypatch):
    async def fake_benchmark(model_id: str, backend: str = "ollama", *, port: int = 11434):
        return {
            "model_id": model_id,
            "backend": backend,
            "latency_ms": 95.0,
            "tokens_per_sec": 18.5,
            "source": "live",
            "port": port,
        }

    monkeypatch.setattr("keprix.playbook.routes.run_model_benchmark", fake_benchmark)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/playbook/benchmark",
            json={"model_id": "llama3.1-8b-q4", "backend": "ollama"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["latency_ms"] == 95.0
    assert data["tokens_per_sec"] == 18.5
    assert data["source"] == "live"
