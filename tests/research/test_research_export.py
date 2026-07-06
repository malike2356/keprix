"""Tests for deep research job export."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.export.renderer import export_document
from keprix.research.export import build_research_export_markdown, export_research_job
from keprix.research.store import ResearchJob


@pytest.fixture(autouse=True)
def mock_research_runtime(monkeypatch):
    async def fake_complete(prompt, *, model=None, user_id=None, session_id=None):
        lowered = prompt.lower()
        if "break this research question" in lowered:
            return "\n".join(f"What should we know about aspect {i + 1}?" for i in range(8))
        return (
            "## Executive Summary\n\n"
            "- Key finding for export test [1].\n\n"
            "## Findings\n\n"
            "Detailed analysis with citation [1].\n\n"
            "## Sources\n\n"
            "[1] Example source - https://example.org/source\n"
        )

    async def fake_search(query, limit=5):
        return [
            {
                "title": f"Source for {query}",
                "url": "https://example.org/source",
                "snippet": "Relevant context.",
            }
        ]

    monkeypatch.setattr("keprix.research.inference.complete_research_prompt", fake_complete)
    monkeypatch.setattr("keprix.research.search.web_search", fake_search)


def _sample_job() -> ResearchJob:
    return ResearchJob(
        id="rsch-abc12345",
        user_id="local",
        query="Borehole business opportunities in Ghana",
        depth="quick",
        status="complete",
        report_markdown=(
            "<!-- keprix-research words:~500 elapsed_s:12.0 -->\n"
            "# Research Report\n\n"
            "**Query:** Borehole business opportunities in Ghana\n\n"
            "## Executive Summary\n\n"
            "- Market demand is rising [1].\n"
        ),
        sources=[{"title": "Example", "url": "https://example.org/source"}],
    )


def test_build_research_export_markdown_strips_internal_header() -> None:
    job = _sample_job()
    markdown = build_research_export_markdown(job)
    assert "<!-- keprix-research" not in markdown
    assert "# Research Report" not in markdown.splitlines()[0] if markdown else True
    assert "Executive Summary" in markdown
    assert "rsch-abc12345" not in markdown


def test_export_research_job_html_includes_cover_and_query() -> None:
    result = export_research_job(_sample_job(), format="html", include_cover=True)
    assert result["format"] == "html"
    html_doc = result["content"]
    assert "cover-page" in html_doc
    assert "Borehole business opportunities in Ghana" in html_doc
    assert "research-report" in html_doc
    assert result.get("renderer") == "html"


def test_export_research_job_pdf_uses_weasyprint_when_available() -> None:
    result = export_research_job(_sample_job(), format="pdf", include_cover=True)
    assert result["format"] == "pdf"
    assert result["content"][:4] == b"%PDF"
    from keprix.export.pdf_engine import weasyprint_available

    if weasyprint_available():
        assert result.get("renderer") == "weasyprint"
        assert len(result["content"]) > 5000
    else:
        assert result.get("renderer") == "text-fallback"


def test_export_research_job_markdown_includes_front_matter() -> None:
    result = export_research_job(_sample_job(), format="markdown", include_cover=False)
    assert result["format"] == "markdown"
    assert "run_id: rsch-abc12345" in result["content"]
    assert "<!-- keprix-research" not in result["content"]


def test_export_document_pdf_uses_composed_html_with_cover() -> None:
    result = export_document(
        title="Covered PDF",
        content="# Section\n\nExport body.",
        format="pdf",
        include_cover=True,
        cover_data={"document_type": "Deep Research Report", "document_id": "rsch-test0001"},
        html_template="research",
    )
    assert result["content"][:4] == b"%PDF"


@pytest.mark.asyncio
async def test_research_export_api_running_job_returns_409():
    from keprix.research.store import get_research_store

    store = get_research_store()
    job = await store.create(user_id="local", query="export running guard", depth="quick")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/research/jobs/{job.id}/export?format=markdown")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_research_export_api_markdown_and_html():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        start = await client.post(
            "/api/research/start",
            json={"query": "renewable energy export test", "depth": "quick"},
        )
        job_id = start.json()["job_id"]
        for _ in range(40):
            status = await client.get(f"/api/research/jobs/{job_id}")
            if status.json().get("status") in {"complete", "failed", "error"}:
                break
            import asyncio

            await asyncio.sleep(0.25)

        md = await client.get(f"/api/research/jobs/{job_id}/export?format=markdown")
        assert md.status_code == 200
        assert "renewable energy export test" in md.text
        assert "<!-- keprix-research" not in md.text

        html = await client.get(f"/api/research/jobs/{job_id}/export?format=html")
        assert html.status_code == 200
        assert "renewable energy export test" in html.text
        assert "cover-page" in html.text


@pytest.mark.asyncio
async def test_research_export_api_pdf():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        start = await client.post(
            "/api/research/start",
            json={"query": "pdf export smoke test", "depth": "quick"},
        )
        job_id = start.json()["job_id"]
        for _ in range(40):
            status = await client.get(f"/api/research/jobs/{job_id}")
            if status.json().get("status") in {"complete", "failed", "error"}:
                break
            import asyncio

            await asyncio.sleep(0.25)

        response = await client.get(f"/api/research/jobs/{job_id}/export?format=pdf")
        assert response.status_code == 200
        if response.headers.get("content-type", "").startswith("application/pdf"):
            assert response.content[:4] == b"%PDF"
        else:
            pytest.skip("WeasyPrint unavailable; server returned HTML fallback")
