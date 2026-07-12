"""Run-completion hooks for the Agent OS run ledger."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from typing import Any

from keprix.agent_os.run_ledger import RunLedgerEntry
from keprix.agent_os.run_ledger_store import RunLedgerStore
from keprix.integrations.scout_lifecycle_client import emit_scout_lifecycle_event

if TYPE_CHECKING:
    from keprix.playbook.runtime.state import PlaybookRun


def _last_payload(events: list[dict[str, Any]], key: str) -> dict[str, Any]:
    for event in reversed(events):
        payload = event.get("payload") or {}
        if isinstance(payload.get(key), dict):
            return dict(payload[key])
    return {}


def _duration_ms(events: list[dict[str, Any]]) -> int:
    return sum(
        int((event.get("payload") or {}).get("duration_ms") or 0)
        for event in events
        if event.get("event_type") == "playbook.node.completed"
    )


def _tokens(state: dict[str, Any]) -> int:
    usage = state.get("_token_usage") or state.get("token_usage") or state.get("tokens")
    if isinstance(usage, dict):
        return int(usage.get("total") or usage.get("total_tokens") or 0)
    return int(usage or 0)


def _eval_score(state: dict[str, Any]) -> float | None:
    value = state.get("_eval_score") or state.get("eval_score")
    if value is None:
        return None
    return float(value)


def record_playbook_run_completion(run: "PlaybookRun", events: list[dict[str, Any]]) -> RunLedgerEntry:
    entry = RunLedgerEntry.create(
        source_type="playbook",
        source_id=str(run.state.get("_playbook_id") or run.graph_id),
        run_id=run.run_id,
        workspace_id=run.workspace_id,
        status=run.status.value,
        input_summary=_last_payload(events, "input_state"),
        output_summary={
            **_last_payload(events, "output_state"),
            "approval_backlog": 1 if run.approval_request else 0,
            "error": run.error,
        },
        eval_score=_eval_score(run.state),
        tokens=_tokens(run.state),
        duration_ms=_duration_ms(events),
        user_corrections=list(run.state.get("_user_corrections") or run.state.get("user_corrections") or []),
    )
    RunLedgerStore().add(entry)
    from keprix.playbook.run_telemetry import enrich_run_completion

    payload = enrich_run_completion(
        run,
        playbook_id=entry.source_id,
        version_hash=str(run.state.get("_playbook_version_hash")) if run.state.get("_playbook_version_hash") else None,
        events=events,
    )
    payload["ledger_entry_id"] = entry.entry_id
    try:
        asyncio.create_task(emit_scout_lifecycle_event("run.completed", payload, workspace_id=run.workspace_id))
    except RuntimeError:
        pass
    return entry


def record_external_run(
    *,
    source_type: str,
    source_id: str,
    run_id: str,
    workspace_id: str,
    status: str,
    input_summary: dict[str, Any] | None = None,
    output_summary: dict[str, Any] | None = None,
    eval_score: float | None = None,
    tokens: int = 0,
    duration_ms: int = 0,
    user_corrections: list[str] | None = None,
) -> RunLedgerEntry:
    entry = RunLedgerEntry.create(
        source_type=source_type,
        source_id=source_id,
        run_id=run_id,
        workspace_id=workspace_id,
        status=status,
        input_summary=input_summary,
        output_summary=output_summary,
        eval_score=eval_score,
        tokens=tokens,
        duration_ms=duration_ms,
        user_corrections=user_corrections,
    )
    return RunLedgerStore().add(entry)
