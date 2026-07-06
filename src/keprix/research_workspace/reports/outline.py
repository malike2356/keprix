"""Build report outlines from research project artifacts."""

from __future__ import annotations

from typing import Any

from keprix.research_workspace.citations.registry import CitationLibrary
from keprix.research_workspace.reports.schemas import ReportOutline, ReportType
from keprix.research_workspace.reports.templates import build_section, default_title, section_order


def _list_sources(store: Any, project_id: str) -> list[dict[str, Any]]:
    with store.plane.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM research_sources WHERE project_id = ? ORDER BY retrieved_at",
            (project_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def _list_claims(store: Any, project_id: str) -> list[dict[str, Any]]:
    with store.plane.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM research_claims WHERE project_id = ? ORDER BY created_at",
            (project_id,),
        ).fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["approved"] = bool(item.get("approved"))
        results.append(item)
    return results


def build_outline(
    store: Any,
    project_id: str,
    *,
    report_type: ReportType,
    title: str | None = None,
    approved_claims_only: bool = False,
) -> ReportOutline:
    project = store.get_project(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    sources = _list_sources(store, project_id)
    claims = _list_claims(store, project_id)
    if approved_claims_only:
        claims = [claim for claim in claims if claim.get("approved")]

    datasets = [
        item
        for item in store.list_objects(project_id, object_type="dataset")
    ]
    artifacts = store.list_objects(project_id)
    citations = CitationLibrary(store).list_cached(project_id)

    sections = [
        build_section(
            key,
            project_title=project.get("title") or project_id,
            question=project.get("question"),
            sources=sources,
            claims=claims,
            datasets=datasets,
        )
        for key in section_order(report_type)
    ]

    return ReportOutline(
        project_id=project_id,
        title=title or project.get("title") or default_title(report_type),
        question=project.get("question"),
        report_type=report_type,
        sections=sections,
        citation_keys=[record.citation_key for record in citations],
        claim_ids=[str(claim.get("claim_id")) for claim in claims if claim.get("claim_id")],
        source_ids=[str(source.get("source_id")) for source in sources if source.get("source_id")],
        artifact_ids=[str(item.get("object_id")) for item in artifacts if item.get("object_id")],
    )
