"""Performance and recovery hardening helpers for the Keprix TUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from keprix.tui.command_center.states import TuiStateView, get_tui_state


@dataclass(frozen=True)
class LatencyBudgets:
    slash_open_ms: float = 50.0
    slash_filter_500_ms: float = 30.0
    transcript_append_ms: float = 16.0
    virtual_window_10k_ms: float = 25.0
    interrupt_schedule_ms: float = 50.0
    resize_refresh_ms: float = 50.0


@dataclass(frozen=True)
class MemoryBudgets:
    runtime_store_bytes: int = 2_000_000
    transcript_virtual_bytes: int = 5_000_000
    render_snapshot_bytes: int = 2_000_000
    queue_bytes: int = 1_000_000


HTTP_ERROR_MESSAGES = {
    400: "Request was rejected by the backend.",
    401: "Session is not authenticated. Sign in again.",
    403: "You do not have permission for this action.",
    404: "The requested session or endpoint was not found.",
    408: "Backend timed out before completing the request.",
    429: "Rate limit reached. Wait and try again.",
    500: "Backend error. Retry after the service recovers.",
}


def clear_error_message(status_code: int, *, detail: str = "") -> str:
    base = HTTP_ERROR_MESSAGES.get(status_code, "Backend request failed.")
    detail = detail.strip()
    return f"{base} {detail}".strip()


def state_for_http_status(status_code: int) -> TuiStateView:
    if status_code == 401:
        return get_tui_state("auth_expired")
    if status_code == 403:
        return get_tui_state("forbidden_action")
    if status_code == 429:
        return get_tui_state("rate_limited")
    if status_code >= 500:
        return get_tui_state("server_error")
    return get_tui_state("backend_offline")


def safe_stream_json_line(line: str) -> dict[str, Any] | None:
    import json

    if not line.strip():
        return None
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return {"type": "error", "message": "Backend sent an invalid stream line."}
    return payload if isinstance(payload, dict) else {"type": "error", "message": "Backend stream line was not an object."}


def coalesce_resize_events(events: list[tuple[int, int]]) -> tuple[int, int] | None:
    return events[-1] if events else None


def terminal_too_small(width: int, height: int) -> bool:
    return width < 40 or height < 10


def queue_payload_bytes(items: list[str]) -> int:
    return sum(len(item.encode("utf-8")) for item in items)


def assert_no_traceback(text: str) -> None:
    assert "Traceback (most recent call last)" not in text
    assert "AttributeError:" not in text
    assert "HTTPStatusError:" not in text


__all__ = [
    "LatencyBudgets",
    "MemoryBudgets",
    "assert_no_traceback",
    "clear_error_message",
    "coalesce_resize_events",
    "queue_payload_bytes",
    "safe_stream_json_line",
    "state_for_http_status",
    "terminal_too_small",
]
