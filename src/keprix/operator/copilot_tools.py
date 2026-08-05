"""Read-only and approval-gated tools for the Keprix operator copilot."""

from __future__ import annotations

from typing import Any

from keprix.operator.context_bundle import (
    _channel_issues,
    _interrupted_playbook_runs,
    _recent_failed_playbook_runs,
    _staged_mutation_count_sync,
)


class CopilotToolError(ValueError):
    """Tool invocation failed."""


def list_staged_mutations(workspace_id: str = "default") -> list[dict[str, str]]:
    try:
        from keprix.mutation.store import get_mutation_store

        store = get_mutation_store()
        items, _total = store.list_mutations(workspace_id, status="staged", page=1, per_page=50)
        return [
            {
                "id": item.id,
                "name": item.name,
                "tier": item.tier,
                "trigger": item.trigger,
                "status": item.status,
            }
            for item in items
        ]
    except Exception as exc:
        raise CopilotToolError(str(exc)) from exc


def list_interrupted_playbooks(workspace_id: str = "default") -> list[dict[str, str]]:
    return _interrupted_playbook_runs(workspace_id)


async def get_channel_status() -> list[dict[str, str]]:
    issues = await _channel_issues()
    if issues:
        return issues
    return [{"id": "all", "name": "All channels", "status": "healthy", "detail": "No channel issues detected."}]


def get_playbook_run_summary(run_id: str, *, workspace_id: str = "default") -> dict[str, str]:
    try:
        from keprix.playbook.runtime import playbook_registry

        run = playbook_registry.get(run_id)
        if run is None or (workspace_id and run.workspace_id != workspace_id):
            raise CopilotToolError(f"Playbook run '{run_id}' not found")
        return {
            "run_id": run.run_id,
            "graph_id": run.graph_id,
            "status": run.status.value,
            "error": (run.error or "")[:240],
            "current_node": run.current_node or "",
            "interrupt_reason": run.interrupt_reason or "",
        }
    except CopilotToolError:
        raise
    except Exception as exc:
        raise CopilotToolError(str(exc)) from exc


def approve_mutation(record_id: str, *, confirmed: bool = False) -> dict[str, Any]:
    if not confirmed:
        return {
            "status": "approval_required",
            "action": "approve_mutation",
            "record_id": record_id,
            "message": "Confirm to approve this staged mutation.",
        }
    try:
        from keprix.mutation.store import get_mutation_store

        store = get_mutation_store()
        record = store.approve_mutation(record_id, approved_by="operator_copilot")
        if record.status == "approved":
            generated_dir = store.generated_tools_dir()
            store.write_tool_to_disk(record, generated_dir)
            store.reload_registry(generated_dir)
        return {"status": "approved", "record_id": record.id, "name": record.name}
    except Exception as exc:
        raise CopilotToolError(str(exc)) from exc


async def resume_playbook_run(run_id: str, *, confirmed: bool = False) -> dict[str, Any]:
    if not confirmed:
        return {
            "status": "approval_required",
            "action": "resume_playbook_run",
            "run_id": run_id,
            "message": "Confirm to resume this playbook run.",
        }
    try:
        from keprix.playbook.runtime import playbook_registry

        run = await playbook_registry.resume(run_id, approved_by="operator_copilot")
        return {
            "status": run.status.value,
            "run_id": run.run_id,
            "graph_id": run.graph_id,
        }
    except Exception as exc:
        raise CopilotToolError(str(exc)) from exc


def staged_mutation_count(workspace_id: str = "default") -> int:
    return _staged_mutation_count_sync(workspace_id)


def recent_failed_runs(workspace_id: str = "default", *, limit: int = 3) -> list[dict[str, str]]:
    return _recent_failed_playbook_runs(workspace_id, limit=limit)
