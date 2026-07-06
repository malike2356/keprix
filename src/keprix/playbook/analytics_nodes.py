"""Playbook node handlers for analytics workspace (Prompt 197)."""

from __future__ import annotations

import csv
import io
from typing import Any

from keprix.analytics.workspace_routes import get_workspace_interpreter
from keprix.playbook.runtime.errors import PlaybookGraphError


def _parse_csv_records(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text.strip()))
    return [dict(row) for row in reader]


async def analytics_ingest_node(
    state: dict[str, Any],
    *,
    dataset_name: str = "main",
    data: str | None = None,
) -> dict[str, Any]:
    """Load CSV-like text into the session dataframe memory."""
    raw = (data or state.get("analytics_data") or "").strip()
    if not raw:
        raise PlaybookGraphError("analytics_ingest requires data")

    records = _parse_csv_records(raw)
    if not records:
        raise PlaybookGraphError("analytics_ingest found no rows")

    interpreter = get_workspace_interpreter()
    session_id = state.get("analytics_session_id")
    session = interpreter.get_session(str(session_id)) if session_id else None
    if session is None:
        session = interpreter.create_session()

    schema = session.dataframe_memory.remember_records(dataset_name, records, source="playbook")
    new_state = dict(state)
    new_state["analytics_session_id"] = session.session_id
    new_state["analytics_ingest"] = {
        "dataset": dataset_name,
        "row_count": schema.row_count,
        "columns": list(schema.columns.keys()),
    }
    return new_state


async def analytics_code_node(
    state: dict[str, Any],
    *,
    code: str | None = None,
    dataset_name: str | None = None,
) -> dict[str, Any]:
    """Execute analytics Python inside an existing or new session."""
    run_code = (code or state.get("analytics_code") or "").strip()
    if not run_code:
        raise PlaybookGraphError("analytics_code requires code")

    interpreter = get_workspace_interpreter()
    session_id = state.get("analytics_session_id")
    session = interpreter.get_session(str(session_id)) if session_id else None
    if session is None:
        session = interpreter.create_session()

    dataset = dataset_name or (state.get("analytics_ingest") or {}).get("dataset") or "main"
    records = session.dataframe_memory.get_records(dataset)
    namespace = {
        "records": records,
        "row_count": len(records),
        "dataset_name": dataset,
    }
    verification, result = interpreter.run_code(session, run_code, namespace)

    new_state = dict(state)
    new_state["analytics_session_id"] = session.session_id
    new_state["analytics_result"] = {
        "ok": result.ok,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "verification_passed": verification.allowed,
        "variables": dict(session.variables_metadata),
    }
    return new_state
