"""Research artifacts: datasets, outputs, figures, reports."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.research_workspace.schemas import ExportPolicy, ResearchDataset, SensitivityLevel, new_trace_id


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ArtifactService:
    def __init__(self, store: Any) -> None:
        self.store = store

    def register_dataset(
        self,
        project_id: str,
        *,
        name: str,
        path: str,
        format: str,
        owner: str,
        engine: str | None = None,
        source_id: str | None = None,
    ) -> ResearchDataset:
        dataset_id = f"ds-{uuid.uuid4().hex[:10]}"
        trace_id = new_trace_id()
        row = self.store.save_object(
            object_id=dataset_id,
            object_type="dataset",
            project_id=project_id,
            owner=owner,
            source_ref=path,
            provenance={"source_id": source_id, "registered_from": path},
            payload={"name": name, "format": format, "path": path, "engine": engine},
            trace_id=trace_id,
        )
        project = self.store.get_project(project_id) or {}
        return ResearchDataset(
            workspace_id=project.get("workspace_id") or self.store.plane.workspace_id,
            project_id=project_id,
            owner=owner,
            source_ref=path,
            provenance={"source_id": source_id},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            trace_id=trace_id,
            sensitivity_level=row.get("sensitivity_level") or SensitivityLevel.INTERNAL.value,
            export_policy=row.get("export_policy") or ExportPolicy.ALLOW.value,
            dataset_id=dataset_id,
            name=name,
            format=format,
            path=path,
            engine=engine,
        )

    def register_report(
        self,
        project_id: str,
        *,
        title: str,
        path: str,
        owner: str,
        source_run_id: str | None = None,
    ) -> dict[str, Any]:
        report_id = f"rpt-{uuid.uuid4().hex[:10]}"
        return self.store.save_object(
            object_id=report_id,
            object_type="report",
            project_id=project_id,
            owner=owner,
            source_ref=path,
            provenance={"analysis_run_id": source_run_id},
            payload={"title": title, "path": path},
            trace_id=new_trace_id(),
        )

    def register_analytics_handoff(
        self,
        project_id: str,
        *,
        owner: str,
        title: str,
        summary: str,
        chart_export: dict[str, Any] | list[dict[str, Any]] | None = None,
        analytics_session_id: str | None = None,
    ) -> dict[str, Any]:
        artifact_id = f"art-{uuid.uuid4().hex[:10]}"
        return self.store.save_object(
            object_id=artifact_id,
            object_type="analytics_artifact",
            project_id=project_id,
            owner=owner,
            source_ref=analytics_session_id,
            provenance={"source": "analytics-workspace"},
            payload={
                "title": title,
                "summary": summary,
                "chart_export": chart_export,
                "analytics_session_id": analytics_session_id,
            },
            trace_id=new_trace_id(),
        )
