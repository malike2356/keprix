"""Report outline tests."""

from __future__ import annotations

import uuid

import pytest

from keprix.data_architecture.data_plane import WorkspaceDataPlane
from keprix.research_workspace.evidence import EvidenceService
from keprix.research_workspace.project import ResearchProjectService
from keprix.research_workspace.reports.outline import build_outline
from keprix.research_workspace.source import ResearchSourceService
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


def test_build_literature_review_outline(research_store):
    projects = ResearchProjectService(research_store)
    sources = ResearchSourceService(research_store)
    evidence = EvidenceService(research_store)

    project = projects.create(title="Water study", question="Did levels rise?", owner="analyst")
    source = sources.add(project.project_id, kind="url", ref="https://example.org/paper", owner="analyst")
    evidence.add_claim(
        project.project_id,
        text="Groundwater rose in Q1",
        source_id=source.source_id,
        owner="analyst",
        approved=True,
    )

    outline = build_outline(research_store, project.project_id, report_type="literature_review")
    assert outline.title == "Water study"
    assert outline.question == "Did levels rise?"
    assert len(outline.sections) >= 3
    headings = [section.heading for section in outline.sections]
    assert "Sources" in headings
    assert "Findings" in headings
    assert source.source_id in outline.source_ids


def test_approved_claims_only_filters_outline(research_store):
    projects = ResearchProjectService(research_store)
    evidence = EvidenceService(research_store)
    project = projects.create(title="Filter test", owner="analyst")
    evidence.add_claim(project.project_id, text="Pending claim", source_id=None, owner="analyst", approved=False)
    evidence.add_claim(project.project_id, text="Approved claim", source_id=None, owner="analyst", approved=True)

    outline = build_outline(
        research_store,
        project.project_id,
        report_type="policy_brief",
        approved_claims_only=True,
    )
    assert len(outline.claim_ids) == 1
