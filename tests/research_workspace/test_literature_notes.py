"""Literature note generation tests."""

from __future__ import annotations

import uuid

import pytest

from keprix.data_architecture.data_plane import WorkspaceDataPlane
from keprix.research_workspace.citations.literature_notes import generate_literature_note, literature_note_body
from keprix.research_workspace.citations.models import CitationRecord
from keprix.research_workspace.citations.registry import CitationLibrary
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


def test_literature_note_body_sections():
    record = CitationRecord(
        item_key="item-1",
        citation_key="ada2024paper",
        title="Survey methods",
        authors=["Ada Lovelace"],
        year="2024",
        abstract="A short abstract.",
        tags=["survey"],
    )
    body = literature_note_body(
        record,
        sections={"relevance": "Critical for the borehole study."},
    )
    assert "ada2024paper" in body
    assert "Critical for the borehole study." in body
    assert "## Methods" in body


def test_generate_literature_note_with_frontmatter():
    record = CitationRecord(
        item_key="item-1",
        citation_key="ada2024paper",
        title="Survey methods",
        authors=["Ada Lovelace"],
        year="2024",
        source="better_bibtex",
    )
    generated = generate_literature_note(record, project_id="rp-1", trace_id="trace-1")
    assert generated["citation_key"] == "ada2024paper"
    assert "keprix_project_id" in generated["content"] or "rp-1" in generated["content"]
    assert "review_status" in generated["content"]
    assert "[[index]]" in generated["content"]


def test_citation_library_persists_records(research_store):
    project = research_store.create_project(title="Citation test", owner="user-1")
    record = CitationRecord(
        item_key="item-1",
        citation_key="smith2023water",
        title="Water trends",
        authors=["Smith, John"],
        year="2023",
        source="better_bibtex",
    )
    library = CitationLibrary(research_store)
    library.save_records(project["project_id"], [record])
    loaded = library.list_cached(project["project_id"])
    assert loaded[0].citation_key == "smith2023water"
    assert loaded[0].source == "better_bibtex"
