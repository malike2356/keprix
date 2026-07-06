"""Prompt 14 acceptance tests: blind model comparison."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.compare.service import CompareGenerationResult
from keprix.compare.store import CompareStore, reset_compare_store


@pytest.fixture
def isolated_compare_store(tmp_path: Path):
    store = CompareStore(sqlite_path=tmp_path / "compare.db")
    reset_compare_store(store)
    yield store
    reset_compare_store(None)


@pytest.fixture
def mock_generation(monkeypatch):
    async def fake_pair(prompt: str, model_a: str, model_b: str, *, user_id: str | None = None):
        return (
            CompareGenerationResult(text=f"A:{prompt}", latency_ms=100, model_id=model_a),
            CompareGenerationResult(text=f"B:{prompt}", latency_ms=120, model_id=model_b),
        )

    monkeypatch.setattr("keprix.compare.routes.generate_pair", fake_pair)
    monkeypatch.setattr(
        "keprix.compare.routes.resolve_comparison_models",
        lambda model_a, model_b: (
            model_a or "deepseek:deepseek-chat",
            model_b or "openai:gpt-4.1-mini",
        ),
    )
    monkeypatch.setattr(
        "keprix.compare.routes.list_available_models",
        lambda: [
            {"id": "deepseek:deepseek-chat", "provider": "deepseek", "name": "deepseek-chat"},
            {"id": "openai:gpt-4.1-mini", "provider": "openai", "name": "gpt-4.1-mini"},
        ],
    )


@pytest.mark.asyncio
async def test_compare_start_returns_blind_responses(mock_generation, isolated_compare_store):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/compare/start",
            json={"prompt": "Explain transformers in one paragraph."},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["response_a"].startswith("A:")
    assert data["response_b"].startswith("B:")
    assert data["latency_ms_a"] == 100
    assert "model_a" not in data
    assert "model_b" not in data


@pytest.mark.asyncio
async def test_compare_models_endpoint_lists_configured_models(mock_generation):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/compare/models")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 2
    assert payload["models"][0]["id"]


@pytest.mark.asyncio
async def test_compare_leaderboard_pair_rates_sum_to_100(mock_generation, isolated_compare_store):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        start = await client.post(
            "/api/compare/start",
            json={
                "prompt": "Summarize RAG.",
                "model_a": "deepseek:deepseek-chat",
                "model_b": "openai:gpt-4.1-mini",
                "random_models": False,
            },
        )
        comp_id = start.json()["comparison_id"]
        vote = await client.post(f"/api/compare/{comp_id}/vote", json={"winner": "a"})
        assert vote.status_code == 200
        assert vote.json()["model_a"] == "deepseek:deepseek-chat"
        board = await client.get("/api/compare/leaderboard")
    assert board.status_code == 200
    payload = board.json()
    assert payload["pairs"]
    assert payload["models"]
    for row in payload["pairs"]:
        total = row["a_win_rate_pct"] + row["b_win_rate_pct"] + row["tie_rate_pct"]
        assert abs(total - 100.0) < 0.05


@pytest.mark.asyncio
async def test_compare_history_persists_in_store(mock_generation, isolated_compare_store):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        start = await client.post(
            "/api/compare/start",
            json={"prompt": "History check", "random_models": True},
        )
        comp_id = start.json()["comparison_id"]
        await client.post(f"/api/compare/{comp_id}/vote", json={"winner": "tie"})
        history = await client.get("/api/compare/history")
    assert history.status_code == 200
    rows = history.json()
    assert len(rows) == 1
    assert rows[0]["winner"] == "tie"
    assert rows[0]["latency_ms_a"] == 100


@pytest.mark.asyncio
async def test_compare_start_rejects_identical_models(isolated_compare_store, monkeypatch):
    monkeypatch.setattr(
        "keprix.compare.service.validate_model_id",
        lambda model_id: model_id,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/compare/start",
            json={
                "prompt": "Same model",
                "model_a": "deepseek:deepseek-chat",
                "model_b": "deepseek:deepseek-chat",
                "random_models": False,
            },
        )
    assert response.status_code == 400
