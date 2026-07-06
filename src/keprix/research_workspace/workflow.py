"""Research workflows that orchestrate external tools via playbooks and jobs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.research_workspace.errors import ExternalToolBoundaryError
from keprix.research_workspace.schemas import EXTERNAL_TOOL_OWNERS, AnalysisRun, ExportPolicy, SensitivityLevel, new_trace_id


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


ALLOWED_ADAPTERS = {
    "jamovi": {"mode": "adapter", "job_type": "statistical_analysis", "owns_execution": False},
    "pspp": {"mode": "cli", "job_type": "statistical_analysis", "owns_execution": False},
    "r": {"mode": "cli", "job_type": "statistical_analysis", "owns_execution": False},
    "python": {"mode": "cli", "job_type": "statistical_analysis", "owns_execution": False},
    "jupyter": {"mode": "export", "job_type": "report_generation", "owns_execution": False},
    "pandoc": {"mode": "render", "job_type": "report_generation", "owns_execution": False},
    "quarto": {"mode": "render", "job_type": "report_generation", "owns_execution": False},
    "obsidian": {"mode": "export", "job_type": "obsidian_sync", "owns_execution": False},
    "zotero": {"mode": "import", "job_type": "data_import", "owns_execution": False},
}


class ResearchWorkflowService:
    def __init__(self, store: Any) -> None:
        self.store = store

    def assert_adapter_only(self, tool: str) -> dict[str, Any]:
        normalized = tool.lower()
        if normalized not in EXTERNAL_TOOL_OWNERS:
            raise ExternalToolBoundaryError(f"Unknown external tool `{tool}`")
        adapter = ALLOWED_ADAPTERS.get(normalized)
        if adapter is None:
            raise ExternalToolBoundaryError(f"No adapter registered for `{tool}`")
        if adapter.get("owns_execution"):
            raise ExternalToolBoundaryError(f"keprix must not replace `{tool}` execution")
        return adapter

    def start_analysis_run(
        self,
        project_id: str,
        *,
        tool: str,
        owner: str,
        parameters: dict[str, Any] | None = None,
        dataset_id: str | None = None,
    ) -> AnalysisRun:
        adapter = self.assert_adapter_only(tool)
        run_id = f"arun-{uuid.uuid4().hex[:10]}"
        trace_id = new_trace_id()
        job = self.store.enqueue_research_job(
            job_type=adapter["job_type"],
            payload={
                "project_id": project_id,
                "tool": tool,
                "parameters": parameters or {},
                "dataset_id": dataset_id,
                "adapter_mode": adapter["mode"],
            },
        )
        row = self.store.save_object(
            object_id=run_id,
            object_type="analysis_run",
            project_id=project_id,
            owner=owner,
            source_ref=dataset_id,
            provenance={"tool": tool, "adapter": adapter, "job_id": job.get("job_id")},
            payload={"tool": tool, "status": "queued", "parameters": parameters or {}, "job_id": job.get("job_id")},
            trace_id=trace_id,
        )
        project = self.store.get_project(project_id) or {}
        return AnalysisRun(
            workspace_id=project.get("workspace_id") or self.store.plane.workspace_id,
            project_id=project_id,
            owner=owner,
            source_ref=dataset_id,
            provenance={"tool": tool, "job_id": job.get("job_id")},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            trace_id=trace_id,
            sensitivity_level=row.get("sensitivity_level") or SensitivityLevel.INTERNAL.value,
            export_policy=row.get("export_policy") or ExportPolicy.ALLOW.value,
            run_id=run_id,
            tool=tool,
            status="queued",
            job_id=job.get("job_id"),
            parameters=parameters or {},
        )
