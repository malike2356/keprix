"""Research workspace HTTP routes."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.research_workspace.artifact import ArtifactService
from keprix.research_workspace.errors import (
    ExternalToolBoundaryError,
    PermissionDeniedError,
    ProjectNotFoundError,
    ProvenanceError,
)
from keprix.research_workspace.evidence import EvidenceService
from keprix.research_workspace.obsidian import export_obsidian_vault
from keprix.research_workspace.permissions import assert_can_export, assert_can_read
from keprix.research_workspace.project import ResearchProjectService
from keprix.research_workspace.schemas import EXTERNAL_TOOL_OWNERS, KEPRIX_OWNED_CAPABILITIES
from keprix.research_workspace.source import ResearchSourceService
from keprix.research_workspace.store import get_research_workspace_store
from keprix.research_workspace.reports.report import ReportService
from keprix.research_workspace.reports.evidence_bundle import EvidenceBundleExporter
from keprix.research_workspace.workflow import ResearchWorkflowService

router = APIRouter(prefix="/api/research/projects", tags=["research-workspace"])


class ProjectBody(BaseModel):
    title: str = Field(..., min_length=1)
    question: str | None = None
    sensitivity_level: str = "internal"
    export_policy: str = "allow"


class SourceBody(BaseModel):
    kind: str = "url"
    ref: str = Field(..., min_length=1)
    metadata: dict[str, Any] | None = None


class ClaimBody(BaseModel):
    text: str = Field(..., min_length=1)
    source_id: str | None = None
    confidence: float | None = None
    approved: bool = False


class DatasetBody(BaseModel):
    name: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    format: str = "csv"
    engine: str | None = None
    source_id: str | None = None


class AnalysisRunBody(BaseModel):
    tool: str = Field(..., min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    dataset_id: str | None = None


class EvidenceBundleBody(BaseModel):
    label: str = Field(..., min_length=1)
    summary: str = ""
    member_object_ids: list[str] = Field(default_factory=list)


class ReportGenerateBody(BaseModel):
    report_type: str = "literature_review"
    title: str | None = None
    output_format: str = "markdown"
    approved_claims_only: bool = False
    include_evidence_bundle: bool = True


class EvidenceExportBody(BaseModel):
    label: str = Field(..., min_length=1)
    bundle_id: str | None = None
    member_object_ids: list[str] = Field(default_factory=list)


class AnalyticsArtifactBody(BaseModel):
    title: str = Field(default="Analytics handoff", min_length=1)
    summary: str = ""
    chart_export: dict[str, Any] | list[dict[str, Any]] | None = None
    analytics_session_id: str | None = None


def _user_id(user: dict) -> str:
    return str(user.get("id") or user.get("user_id") or user.get("username") or "default")


def _services():
    store = get_research_workspace_store()
    return {
        "store": store,
        "projects": ResearchProjectService(store),
        "sources": ResearchSourceService(store),
        "evidence": EvidenceService(store),
        "artifacts": ArtifactService(store),
        "workflow": ResearchWorkflowService(store),
        "reports": ReportService(store),
        "evidence_export": EvidenceBundleExporter(store),
    }


@router.get("/boundary")
async def research_boundary() -> dict[str, Any]:
    return {
        "keprix_owns": sorted(KEPRIX_OWNED_CAPABILITIES),
        "external_tools": sorted(EXTERNAL_TOOL_OWNERS),
        "references": {
            "documents": "prompt 69 / src/keprix/documents/",
            "rag_pipeline": "prompt 72 / src/keprix/rag_pipeline/",
            "analytics": "prompt 54 / src/keprix/analytics/",
            "deep_research": "src/keprix/research/",
        },
        "note": "keprix orchestrates external tools; it does not replace Obsidian, Zotero, PSPP, jamovi, R, Python, Jupyter, Pandoc, or Quarto.",
    }


@router.get("")
async def list_projects(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    projects = _services()["projects"].list()
    visible = []
    for project in projects:
        try:
            assert_can_read(
                sensitivity_level=project.sensitivity_level,
                user_id=_user_id(user),
                owner=project.owner,
            )
            visible.append(project.to_dict())
        except PermissionDeniedError:
            continue
    return {"items": visible}


@router.post("")
async def create_project(body: ProjectBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    project = _services()["projects"].create(
        title=body.title,
        question=body.question,
        owner=_user_id(user),
        sensitivity_level=body.sensitivity_level,
        export_policy=body.export_policy,
    )
    return {"project": project.to_dict()}


@router.get("/{project_id}")
async def get_project(project_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        project = _services()["projects"].get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    assert_can_read(
        sensitivity_level=project.sensitivity_level,
        user_id=_user_id(user),
        owner=project.owner,
    )
    store = _services()["store"]
    return {
        "project": project.to_dict(),
        "objects": store.list_objects(project_id),
        "citations": store.list_citations(project_id),
    }


@router.post("/{project_id}/sources")
async def add_source(project_id: str, body: SourceBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    services = _services()
    if services["store"].get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    source = services["sources"].add(
        project_id,
        kind=body.kind,
        ref=body.ref,
        owner=_user_id(user),
        metadata=body.metadata,
    )
    return {"source": source.to_dict()}


@router.post("/{project_id}/claims")
async def add_claim(project_id: str, body: ClaimBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    services = _services()
    try:
        claim = services["evidence"].add_claim(
            project_id,
            text=body.text,
            source_id=body.source_id,
            owner=_user_id(user),
            confidence=body.confidence,
            approved=body.approved,
        )
    except ProvenanceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"claim": claim}


@router.get("/{project_id}/citations")
async def list_citations(project_id: str, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    store = _services()["store"]
    if store.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"items": store.list_citations(project_id)}


@router.post("/{project_id}/datasets")
async def register_dataset(project_id: str, body: DatasetBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    services = _services()
    if services["store"].get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    dataset = services["artifacts"].register_dataset(
        project_id,
        name=body.name,
        path=body.path,
        format=body.format,
        owner=_user_id(user),
        engine=body.engine,
        source_id=body.source_id,
    )
    return {"dataset": dataset.to_dict()}


@router.post("/{project_id}/artifacts")
async def create_analytics_artifact(
    project_id: str,
    body: AnalyticsArtifactBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    services = _services()
    if services["store"].get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    artifact = services["artifacts"].register_analytics_handoff(
        project_id,
        owner=_user_id(user),
        title=body.title,
        summary=body.summary,
        chart_export=body.chart_export,
        analytics_session_id=body.analytics_session_id,
    )
    return {"artifact": artifact}


@router.post("/{project_id}/analysis-runs")
async def start_analysis_run(
    project_id: str,
    body: AnalysisRunBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    services = _services()
    if services["store"].get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        run = services["workflow"].start_analysis_run(
            project_id,
            tool=body.tool,
            owner=_user_id(user),
            parameters=body.parameters,
            dataset_id=body.dataset_id,
        )
    except ExternalToolBoundaryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"analysis_run": run.to_dict()}


@router.post("/{project_id}/evidence-bundles")
async def create_evidence_bundle(
    project_id: str,
    body: EvidenceBundleBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    services = _services()
    try:
        bundle = services["evidence"].build_bundle(
            project_id,
            label=body.label,
            owner=_user_id(user),
            member_object_ids=body.member_object_ids or None,
            summary=body.summary,
        )
    except ProvenanceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"bundle": bundle.to_dict()}


@router.get("/{project_id}/lineage/{object_id}")
async def object_lineage(project_id: str, object_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    services = _services()
    project = services["store"].get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    assert_can_read(
        sensitivity_level=project.get("sensitivity_level") or "internal",
        user_id=_user_id(user),
        owner=project.get("owner") or "default",
    )
    try:
        chain = services["evidence"].trace_lineage(project_id, object_id)
    except ProvenanceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"lineage": chain}


@router.post("/{project_id}/reports/generate")
async def generate_report(
    project_id: str,
    body: ReportGenerateBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    services = _services()
    project = services["store"].get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    assert_can_read(
        sensitivity_level=project.get("sensitivity_level") or "internal",
        user_id=_user_id(user),
        owner=project.get("owner") or "default",
    )
    try:
        result = services["reports"].generate(
            project_id,
            report_type=body.report_type,  # type: ignore[arg-type]
            owner=_user_id(user),
            title=body.title,
            output_format=body.output_format,  # type: ignore[arg-type]
            approved_claims_only=body.approved_claims_only,
            include_evidence_bundle=body.include_evidence_bundle,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result


@router.post("/{project_id}/evidence-bundles/export")
async def export_evidence_bundle(
    project_id: str,
    body: EvidenceExportBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    services = _services()
    project = services["store"].get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        assert_can_export(
            export_policy=project.get("export_policy") or "allow",
            user_id=_user_id(user),
            owner=project.get("owner") or "default",
        )
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    package = services["evidence_export"].build_export_package(
        project_id,
        label=body.label,
        bundle_id=body.bundle_id,
        member_object_ids=body.member_object_ids or None,
    )
    return {"export": package.to_dict()}


@router.post("/{project_id}/export/obsidian")
async def export_obsidian(project_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    store = _services()["store"]
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        assert_can_export(
            export_policy=project.get("export_policy") or "allow",
            user_id=_user_id(user),
            owner=project.get("owner") or "default",
        )
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    with tempfile.TemporaryDirectory() as tmp:
        result = export_obsidian_vault(store, project_id, Path(tmp))
        return result
