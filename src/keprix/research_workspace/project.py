"""Research project lifecycle."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.research_workspace.errors import ProjectNotFoundError
from keprix.research_workspace.schemas import (
    ExportPolicy,
    ResearchProject,
    SensitivityLevel,
    new_trace_id,
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResearchProjectService:
    def __init__(self, store: Any) -> None:
        self.store = store

    def create(
        self,
        *,
        title: str,
        question: str | None = None,
        owner: str = "default",
        sensitivity_level: str = SensitivityLevel.INTERNAL.value,
        export_policy: str = ExportPolicy.ALLOW.value,
    ) -> ResearchProject:
        trace_id = new_trace_id()
        row = self.store.create_project(
            title=title,
            question=question,
            owner=owner,
            trace_id=trace_id,
            sensitivity_level=sensitivity_level,
            export_policy=export_policy,
        )
        return self._to_project(row)

    def get(self, project_id: str) -> ResearchProject:
        row = self.store.get_project(project_id)
        if row is None:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        return self._to_project(row)

    def list(self) -> list[ResearchProject]:
        return [self._to_project(row) for row in self.store.list_projects()]

    def _to_project(self, row: dict[str, Any]) -> ResearchProject:
        return ResearchProject(
            workspace_id=row.get("workspace_id") or self.store.plane.workspace_id,
            project_id=row["project_id"],
            owner=row.get("owner") or "default",
            source_ref=None,
            provenance={"created_by": "research_workspace"},
            created_at=row["created_at"],
            updated_at=row.get("updated_at") or row["created_at"],
            trace_id=row.get("trace_id") or new_trace_id(),
            sensitivity_level=row.get("sensitivity_level") or SensitivityLevel.INTERNAL.value,
            export_policy=row.get("export_policy") or ExportPolicy.ALLOW.value,
            title=row["title"],
            question=row.get("question"),
            status=row.get("status") or "active",
        )
