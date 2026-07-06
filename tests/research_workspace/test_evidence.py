"""Evidence and lineage tests."""

from __future__ import annotations

import uuid

import pytest

from keprix.data_architecture.data_plane import WorkspaceDataPlane
from keprix.research_workspace.errors import ProvenanceError
from keprix.research_workspace.evidence import EvidenceService
from keprix.research_workspace.project import ResearchProjectService
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


def test_claim_requires_registered_source(research_store):
    project = ResearchProjectService(research_store).create(title="Policy review", owner="user-1")
    evidence = EvidenceService(research_store)
    with pytest.raises(ProvenanceError):
        evidence.add_claim(project.project_id, text="Unsupported claim", source_id="missing", owner="user-1")


def test_evidence_bundle_and_lineage(research_store):
    projects = ResearchProjectService(research_store)
    sources = ResearchSourceService(research_store)
    evidence = EvidenceService(research_store)

    project = projects.create(title="Market scan", owner="user-1")
    source = sources.add(project.project_id, kind="url", ref="https://example.org/report", owner="user-1")
    claim = evidence.add_claim(
        project.project_id,
        text="Demand increased in Q1",
        source_id=source.source_id,
        owner="user-1",
        approved=True,
    )
    bundle = evidence.build_bundle(project.project_id, label="Q1 evidence", owner="user-1")
    assert source.source_id in bundle.members or claim["claim_id"] in bundle.members

    chain = evidence.trace_lineage(project.project_id, claim["claim_id"])
    assert chain
    assert any(item.get("object_type") == "source" or "source_id" in item for item in chain)
