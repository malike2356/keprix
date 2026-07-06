"""Prompt 14 acceptance tests: deep research."""

from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.research.errors import ResearchConfigError


@pytest.fixture(autouse=True)
def mock_research_runtime(monkeypatch):
    async def fake_complete(prompt, *, model=None, user_id=None, session_id=None):
        lowered = prompt.lower()
        if "break this research question" in lowered:
            return "\n".join(f"What should we know about aspect {i + 1}?" for i in range(5))
        return (
            "## Executive Summary\n\n"
            "- Ghana borehole demand is rising [1].\n"
            "- Licensing and equipment costs shape entry barriers [2].\n\n"
            "## Findings\n\n"
            "### Market overview\n\n"
            "Operators need permits and reliable rigs [1].\n\n"
            "## Sources\n\n"
            "[1] Example source\n"
        )

    async def fake_search(query, limit=5):
        return [
            {
                "title": f"Research source for {query}",
                "url": f"https://example.org/{abs(hash(query)) % 10000}",
                "snippet": "Relevant market context.",
            }
        ]

    monkeypatch.setattr("keprix.research.inference.complete_research_prompt", fake_complete)
    monkeypatch.setattr("keprix.research.search.web_search", fake_search)


@pytest.mark.asyncio
async def test_research_start_returns_running_job():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/research/start",
            json={"query": "renewable energy trends", "depth": "quick"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["job_id"]


@pytest.mark.asyncio
async def test_research_sse_emits_progress_and_complete():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        start = await client.post(
            "/api/research/start",
            json={"query": "local LLM serving", "depth": "quick"},
        )
        job_id = start.json()["job_id"]
        stream = await client.get(f"/api/research/jobs/{job_id}/stream")
        assert stream.status_code == 200
        events = []
        for line in stream.text.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
        types = {e.get("type") for e in events}
        assert "sub_question_start" in types
        assert "complete" in types


@pytest.mark.asyncio
async def test_research_report_has_sections_and_sources():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        start = await client.post(
            "/api/research/start",
            json={"query": "edge AI deployment", "depth": "quick"},
        )
        job_id = start.json()["job_id"]
        for _ in range(40):
            status = await client.get(f"/api/research/jobs/{job_id}")
            if status.json().get("status") == "complete":
                break
            import asyncio

            await asyncio.sleep(0.25)
        report = await client.get(f"/api/research/jobs/{job_id}/report")
        assert report.status_code == 200
        md = report.json()["report_markdown"]
        assert md.count("##") >= 3
        assert "Sources" in md or "[1]" in md
        assert "example.com/research/" not in md


@pytest.mark.asyncio
async def test_research_fails_clearly_without_llm_provider(monkeypatch):
    async def missing_provider(prompt, *, model=None, user_id=None, session_id=None):
        raise ResearchConfigError(
            "Provider 'deepseek' is not configured. Add its API key to .env and restart the backend."
        )

    monkeypatch.setattr("keprix.research.inference.complete_research_prompt", missing_provider)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        start = await client.post(
            "/api/research/start",
            json={"query": "borehole business in ghana", "depth": "quick"},
        )
        job_id = start.json()["job_id"]
        for _ in range(40):
            status = await client.get(f"/api/research/jobs/{job_id}")
            if status.json().get("status") in {"failed", "error", "complete"}:
                break
            import asyncio

            await asyncio.sleep(0.25)
        report = await client.get(f"/api/research/jobs/{job_id}/report")
        assert report.status_code == 200
        md = report.json()["report_markdown"]
        assert "not configured" in md.lower()
        assert "example.com/research/" not in md
