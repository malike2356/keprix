"""Extract repeated task patterns from recent workspace sessions."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from keprix.agent_os.audit_store import AuditTask
from keprix.workspace.repository import workspace_repo


def _normalize_request(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip().lower())
    cleaned = re.sub(r"[^\w\s/-]", "", cleaned)
    return cleaned[:160]


def _first_user_message(messages: list[dict[str, Any]]) -> str:
    for message in messages:
        if message.get("role") == "user":
            content = message.get("content", "")
            if isinstance(content, str) and content.strip():
                return content.strip()
    return ""


def _tool_names(messages: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for message in messages:
        for call in message.get("tool_calls") or []:
            name = call.get("name") or call.get("function", {}).get("name")
            if name:
                names.append(str(name))
    return sorted(set(names))


def scan_sessions(user: dict[str, Any], session_count: int = 10) -> tuple[list[AuditTask], list[str]]:
    """Return task candidates and scanned session ids."""
    sessions = workspace_repo.list_sessions(user, limit=session_count, offset=0)
    session_ids: list[str] = []
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in sessions:
        session_id = str(row.get("id") or row.get("session_id") or "")
        if not session_id:
            continue
        session_ids.append(session_id)
        try:
            detail = workspace_repo.get_session(user, session_id)
        except Exception:
            continue
        request = _first_user_message(detail.get("messages") or [])
        if not request:
            continue
        key = _normalize_request(request)
        if len(key) < 12:
            continue
        buckets[key].append(
            {
                "session_id": session_id,
                "request": request,
                "tools": _tool_names(detail.get("messages") or []),
            }
        )

    tasks: list[AuditTask] = []
    for index, (key, items) in enumerate(sorted(buckets.items(), key=lambda kv: -len(kv[1]))):
        if len(items) < 2:
            continue
        sample = items[0]["request"]
        slug = re.sub(r"[^a-z0-9]+", "-", sample.lower())[:40].strip("-") or f"task-{index + 1}"
        tools: list[str] = []
        for item in items:
            tools.extend(item.get("tools") or [])
        tasks.append(
            AuditTask(
                id=f"scan-{index + 1}",
                domain="general",
                description=sample,
                frequency="weekly" if len(items) >= 3 else "ad_hoc",
                desired_output=f"Repeatable output for: {sample[:120]}",
                tools_hint=sorted(set(tools))[:12],
                propose_skill=True,
                propose_automation=len(items) >= 3,
            )
        )
    return tasks, session_ids
