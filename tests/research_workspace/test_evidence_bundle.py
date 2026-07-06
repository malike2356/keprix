"""Enhanced evidence bundle export tests."""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from keprix.data_architecture.data_plane import WorkspaceDataPlane
from keprix.research_workspace.evidence import EvidenceService
from keprix.research_workspace.playbook_runner import ResearchPlaybookRunner
from keprix.research_workspace.project import ResearchProjectService
from keprix.research_workspace.reports.evidence_bundle import EvidenceBundleExporter
from keprix.research_workspace.reports.report import ReportService
from keprix.research_workspace.routes import router as research_workspace_router
from keprix.research_workspace.source import ResearchSourceService
from keprix.research_workspace.store import ResearchWorkspaceStore


@pytest.fixture(autouse=True)
def _auth_disabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")


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

    def _get_store(workspace_id: str = "default") -> ResearchWorkspaceStore:
        return store

    for target in (
        "keprix.research_workspace.store.get_research_workspace_store",
        "keprix.research_workspace.routes.get_research_workspace_store",
        "keprix.research_workspace.playbook_routes.get_research_workspace_store",
    ):
        monkeypatch.setattr(target, _get_store)
    return store


@pytest.fixture
def app():
    test_app = FastAPI()
    test_app.include_router(research_workspace_router)
    return test_app


def test_evidence_export_package_maps_claims_to_sources(research_store):
    projects = ResearchProjectService(research_store)
    sources = ResearchSourceService(research_store)
    evidence = EvidenceService(research_store)

    project = projects.create(title="Bundle export", owner="analyst")
    source = sources.add(project.project_id, kind="url", ref="https://example.org", owner="analyst")
    claim = evidence.add_claim(
        project.project_id,
        text="Demand rose",
        source_id=source.source_id,
        owner="analyst",
        approved=True,
    )

    package = EvidenceBundleExporter(research_store).build_export_package(
        project.project_id,
        label="export",
    )
    assert package.sources
    assert package.claim_evidence_map
    mapped = package.claim_evidence_map[0]
    assert mapped["claim_id"] == claim["claim_id"]
    assert mapped["source_id"] == source.source_id


def test_report_service_generates_markdown_and_bundle(research_store):
    project = ResearchProjectService(research_store).create(title="Report service", owner="analyst")
    result = ReportService(research_store).generate(
        project.project_id,
        report_type="literature_review",
        owner="analyst",
    )
    assert result["report_id"]
    assert "## Bibliography" in result["render"]["markdown"]
    assert result["evidence_bundle"]["export"]["claim_evidence_map"] is not None
    bundle = result["evidence_bundle"].get("bundle")
    if bundle is not None:
        assert bundle["bundle_id"]


def test_playbook_report_handler_generates_report_artifact(research_store):
    project = ResearchProjectService(research_store).create(title="Playbook report", owner="analyst")
    result = ResearchPlaybookRunner(research_store).run(
        project.project_id,
        "literature_review",
        owner="analyst",
        dry_run=False,
    )
    report_steps = [step for step in result["run"]["steps"] if step["action"] == "report.draft_literature_review"]
    assert report_steps
    assert report_steps[0]["artifact_type"] == "report"
    assert report_steps[0]["payload"]["report_id"]


@pytest.mark.asyncio
async def test_api_generate_report_and_export_bundle(app, research_store):
    project = ResearchProjectService(research_store).create(title="API report", owner="analyst")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        generated = await client.post(
            f"/api/research/projects/{project.project_id}/reports/generate",
            json={"report_type": "literature_review", "output_format": "markdown"},
        )
        exported = await client.post(
            f"/api/research/projects/{project.project_id}/evidence-bundles/export",
            json={"label": "api export"},
        )
    assert generated.status_code == 200
    payload = generated.json()
    assert payload["report_id"]
    assert "## Bibliography" in payload["render"]["markdown"]
    assert exported.status_code == 200
    assert exported.json()["export"]["label"] == "api export"
