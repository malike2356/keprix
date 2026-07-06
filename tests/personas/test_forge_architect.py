"""Tests for FORGE architect module."""

from __future__ import annotations

import pytest

from keprix.personas.forge.architect import ArchitectureDecision, ForgeArchitect


@pytest.fixture
def architect() -> ForgeArchitect:
    return ForgeArchitect(workspace_id="ws-forge")


def test_render_adr_includes_title(architect: ForgeArchitect) -> None:
    decision = ArchitectureDecision(
        title="Adopt PostgreSQL",
        context="Need relational storage",
        decision="Use PostgreSQL 16 with connection pooling",
        positive_consequences="Mature ecosystem",
        alternatives="SQLite; not suitable at scale",
    )
    markdown = architect.render_adr(decision)
    assert "Adopt PostgreSQL" in markdown
    assert "PostgreSQL 16" in markdown
    assert "ADR-" in markdown


@pytest.mark.asyncio
async def test_record_adr_via_playbook(architect: ForgeArchitect) -> None:
    decision = ArchitectureDecision(
        title="Use FastAPI",
        context="Async HTTP API required",
        decision="Adopt FastAPI with Pydantic v2",
    )
    result = await architect.record_adr(decision)
    assert result["status"] == "completed"
    assert "FastAPI" in result["markdown"]
    assert len(result["adrs"]) == 1


@pytest.mark.asyncio
async def test_adr_playbook_rejects_empty_decision(architect: ForgeArchitect) -> None:
    decision = ArchitectureDecision(title="Empty", context="No context", decision="")
    graph = architect.build_adr_playbook()
    from keprix.playbook.runtime.runner import PlaybookRunner

    runner = PlaybookRunner(graph.compile())
    run = await runner.execute_inline({"adr_input": decision.to_dict(), "adrs": []})
    review = run.state.get("adr_review", {})
    assert review.get("approved") is False
