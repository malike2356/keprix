"""Report renderer and Pandoc adapter tests."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from keprix.data_architecture.data_plane import WorkspaceDataPlane
from keprix.research_workspace.citations.models import CitationRecord
from keprix.research_workspace.citations.registry import CitationLibrary
from keprix.research_workspace.project import ResearchProjectService
from keprix.research_workspace.reports.outline import build_outline
from keprix.research_workspace.reports.pandoc import render_with_pandoc
from keprix.research_workspace.reports.renderer import render_markdown, render_report
from keprix.research_workspace.store import ResearchWorkspaceStore


@pytest.fixture
def research_store(tmp_path, monkeypatch):
    plane = WorkspaceDataPlane(workspace_id=f"ws-{uuid.uuid4().hex[:6]}")
    plane.root = tmp_path / "workspace"
    plane.db_path = plane.root / "data_plane.sqlite"
    plane.initialize()
    store = ResearchWorkspaceStore(workspace_id=plane.workspace_id)
    store.plane = plane
    monkeypatch.setattr(
        "keprix.research_workspace.store.get_workspace_data_plane",
        lambda workspace_id="default": plane,
    )
    return store


def test_render_markdown_includes_bibliography_and_evidence_map(research_store):
    project = ResearchProjectService(research_store).create(title="Render test", owner="analyst")
    CitationLibrary(research_store).save_records(
        project.project_id,
        [
            CitationRecord(
                item_key="smith2023water",
                citation_key="smith2023water",
                title="Water trends",
                authors=["Smith, J."],
                year="2023",
                source="fixture",
            )
        ],
    )
    outline = build_outline(research_store, project.project_id, report_type="literature_review")
    result = render_markdown(research_store, outline)

    assert "## Bibliography" in result.markdown
    assert "Water trends" in result.markdown
    assert "smith2023water" in result.citation_keys
    assert "## Evidence map" in result.markdown
    assert result.format == "markdown"
    assert result.renderer == "markdown"


def test_render_report_falls_back_when_pandoc_missing(research_store):
    project = ResearchProjectService(research_store).create(title="Pandoc fallback", owner="analyst")
    outline = build_outline(research_store, project.project_id, report_type="client_pdf")
    with patch("keprix.research_workspace.reports.pandoc.pandoc_available", return_value=False):
        result = render_report(research_store, outline, output_format="pdf")
    assert result.format == "markdown"
    assert result.setup_instructions
    assert "Pandoc" in result.setup_instructions


def test_render_with_pandoc_when_available(tmp_path):
    markdown = "# Test\n\nBody.\n"
    with patch("keprix.research_workspace.reports.pandoc.pandoc_available", return_value=True):
        with patch("keprix.research_workspace.reports.pandoc.subprocess.run") as run_mock:
            run_mock.return_value.returncode = 0
            result = render_with_pandoc(
                markdown,
                output_format="html",
                workdir=tmp_path,
                citation_keys=["smith2023water"],
            )
    assert result.format == "html"
    assert result.renderer == "pandoc"
    assert result.output_path
    assert result.citation_keys == ["smith2023water"]
