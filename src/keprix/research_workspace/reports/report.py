"""Report generation service for research projects."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from keprix.research_workspace.evidence import EvidenceService
from keprix.research_workspace.errors import ProvenanceError
from keprix.research_workspace.reports.evidence_bundle import EvidenceBundleExporter
from keprix.research_workspace.reports.outline import build_outline
from keprix.research_workspace.reports.renderer import render_report
from keprix.research_workspace.reports.schemas import OutputFormat, ReportType


class ReportService:
    def __init__(self, store: Any) -> None:
        self.store = store
        self._evidence = EvidenceService(store)
        self._bundle_exporter = EvidenceBundleExporter(store)

    def generate(
        self,
        project_id: str,
        *,
        report_type: ReportType,
        owner: str,
        title: str | None = None,
        output_format: OutputFormat = "markdown",
        approved_claims_only: bool = False,
        include_evidence_bundle: bool = True,
        workdir: Path | None = None,
    ) -> dict[str, Any]:
        if self.store.get_project(project_id) is None:
            raise ValueError(f"Project not found: {project_id}")

        outline = build_outline(
            self.store,
            project_id,
            report_type=report_type,
            title=title,
            approved_claims_only=approved_claims_only,
        )
        render = render_report(
            self.store,
            outline,
            output_format=output_format,
            workdir=workdir or self._report_dir(project_id),
        )

        report_id = f"rpt-{uuid.uuid4().hex[:10]}"
        artifact_payload = {
            "report_id": report_id,
            "report_type": report_type,
            "title": outline.title,
            "format": render.format,
            "renderer": render.renderer,
            "markdown": render.markdown,
            "output_path": render.output_path,
            "setup_instructions": render.setup_instructions,
            "citation_keys": render.citation_keys,
            "evidence_links": render.evidence_links,
            "outline": outline.to_dict(),
        }
        self.store.save_object(
            object_id=report_id,
            object_type="report",
            project_id=project_id,
            owner=owner,
            source_ref=render.output_path,
            provenance={
                "report_type": report_type,
                "renderer": render.renderer,
                "citation_keys": render.citation_keys,
            },
            payload=artifact_payload,
            trace_id=report_id,
        )

        bundle_payload: dict[str, Any] | None = None
        if include_evidence_bundle:
            member_ids = list(outline.artifact_ids or [])
            if report_id not in member_ids:
                member_ids.append(report_id)
            try:
                bundle = self._evidence.build_bundle(
                    project_id,
                    label=f"{outline.title} evidence",
                    owner=owner,
                    member_object_ids=member_ids,
                    summary=f"Evidence bundle for report {report_id}",
                )
            except ProvenanceError:
                bundle = None
            if bundle is not None:
                export_package = self._bundle_exporter.build_export_package(
                    project_id,
                    label=bundle.label,
                    bundle_id=bundle.bundle_id,
                    member_object_ids=bundle.members,
                )
                bundle_payload = {
                    "bundle": bundle.to_dict(),
                    "export": export_package.to_dict(),
                }
            else:
                export_package = self._bundle_exporter.build_export_package(
                    project_id,
                    label=f"{outline.title} evidence",
                    bundle_id=None,
                    member_object_ids=[report_id],
                )
                bundle_payload = {"bundle": None, "export": export_package.to_dict()}

        return {
            "report_id": report_id,
            "outline": outline.to_dict(),
            "render": render.to_dict(),
            "evidence_bundle": bundle_payload,
        }

    def _report_dir(self, project_id: str) -> Path:
        base = self.store.plane.root / "reports" / project_id
        base.mkdir(parents=True, exist_ok=True)
        return base
