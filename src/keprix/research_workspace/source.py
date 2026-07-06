"""Research sources and citations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from keprix.research_workspace.schemas import ExportPolicy, ResearchSource, SensitivityLevel, new_trace_id


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResearchSourceService:
    def __init__(self, store: Any) -> None:
        self.store = store

    def add(
        self,
        project_id: str,
        *,
        kind: str,
        ref: str,
        owner: str,
        metadata: dict[str, Any] | None = None,
        sensitivity_level: str = SensitivityLevel.INTERNAL.value,
        export_policy: str = ExportPolicy.ALLOW.value,
    ) -> ResearchSource:
        trace_id = new_trace_id()
        row = self.store.add_source(
            project_id,
            kind=kind,
            ref=ref,
            metadata=metadata,
            owner=owner,
            trace_id=trace_id,
            sensitivity_level=sensitivity_level,
            export_policy=export_policy,
        )
        project = self.store.get_project(project_id) or {}
        return ResearchSource(
            workspace_id=project.get("workspace_id") or self.store.plane.workspace_id,
            project_id=project_id,
            owner=owner,
            source_ref=ref,
            provenance={"ingested_via": "research_workspace", "kind": kind},
            created_at=_utcnow(),
            updated_at=_utcnow(),
            trace_id=trace_id,
            sensitivity_level=sensitivity_level,
            export_policy=export_policy,
            source_id=row["source_id"],
            kind=kind,
            ref=ref,
            metadata=metadata or {},
        )

    def add_citation(
        self,
        project_id: str,
        *,
        label: str,
        source_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.store.add_citation(project_id, label=label, source_id=source_id, metadata=metadata)
