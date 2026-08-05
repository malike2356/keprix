"""Shared empty, loading, and error states for the TUI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TuiStateView:
    id: str
    title: str
    explanation: str
    suggested_action: str
    command_palette_action_id: str = ""
    retry_action: str = ""


STATE_IDS = (
    "empty_transcript",
    "empty_sessions",
    "empty_skills",
    "empty_plugins",
    "empty_search_results",
    "loading_sessions",
    "loading_models",
    "loading_runtime_data",
    "backend_offline",
    "auth_expired",
    "forbidden_action",
    "rate_limited",
    "server_error",
    "stream_interrupted",
    "tool_failed",
    "terminal_too_small",
)


TUI_STATES: dict[str, TuiStateView] = {
    "empty_transcript": TuiStateView(
        "empty_transcript",
        "No messages yet",
        "This session is ready, but no prompt has been sent.",
        "Type a message or open the command palette.",
        "ui:help",
    ),
    "empty_sessions": TuiStateView(
        "empty_sessions",
        "No saved sessions",
        "There are no previous conversations to show.",
        "Start a new chat.",
        "slash:/new",
    ),
    "empty_skills": TuiStateView(
        "empty_skills",
        "No skills loaded",
        "No local skills were reported by the runtime.",
        "Reconnect after installing or enabling skills.",
        "runtime:reconnect",
        "reconnect",
    ),
    "empty_plugins": TuiStateView(
        "empty_plugins",
        "No plugins loaded",
        "No plugins were reported by the runtime.",
        "Reconnect after installing or enabling plugins.",
        "runtime:reconnect",
        "reconnect",
    ),
    "empty_search_results": TuiStateView(
        "empty_search_results",
        "No matches",
        "The current transcript has no matching text.",
        "Try a broader search term.",
    ),
    "loading_sessions": TuiStateView(
        "loading_sessions",
        "Loading sessions",
        "Keprix is asking the runtime for recent conversations.",
        "Wait a moment or reconnect if this does not finish.",
        "runtime:reconnect",
        "reconnect",
    ),
    "loading_models": TuiStateView(
        "loading_models",
        "Loading models",
        "Keprix is checking available model providers.",
        "Wait a moment or open setup if no model appears.",
        "slash:/setup",
    ),
    "loading_runtime_data": TuiStateView(
        "loading_runtime_data",
        "Loading runtime data",
        "Runtime panels are waiting for agent events.",
        "Send a message or reconnect.",
        "runtime:reconnect",
        "reconnect",
    ),
    "backend_offline": TuiStateView(
        "backend_offline",
        "Backend offline",
        "The TUI cannot reach the Keprix runtime.",
        "Start Keprix or reconnect.",
        "runtime:reconnect",
        "reconnect",
    ),
    "auth_expired": TuiStateView(
        "auth_expired",
        "Sign in again",
        "The runtime rejected the current credentials.",
        "Refresh credentials, then reconnect.",
        "runtime:reconnect",
        "reconnect",
    ),
    "forbidden_action": TuiStateView(
        "forbidden_action",
        "Action not allowed",
        "The runtime denied this action for the current user or workspace.",
        "Choose another action or ask an operator to grant access.",
        "ui:help",
    ),
    "rate_limited": TuiStateView(
        "rate_limited",
        "Rate limited",
        "The provider or runtime is temporarily limiting requests.",
        "Wait, then retry the last action.",
        "",
        "retry",
    ),
    "server_error": TuiStateView(
        "server_error",
        "Server error",
        "The runtime failed while processing the request.",
        "Retry after the service recovers.",
        "runtime:reconnect",
        "reconnect",
    ),
    "stream_interrupted": TuiStateView(
        "stream_interrupted",
        "Stream interrupted",
        "The current agent stream stopped before completion.",
        "Review partial output, then retry if needed.",
        "ui:review",
        "retry",
    ),
    "tool_failed": TuiStateView(
        "tool_failed",
        "Tool failed",
        "A tool returned an error for the current turn.",
        "Open review mode or inspect details.",
        "ui:review",
    ),
    "terminal_too_small": TuiStateView(
        "terminal_too_small",
        "Terminal too small",
        "The current terminal size cannot show the TUI reliably.",
        "Resize to at least 40 columns by 10 rows.",
    ),
}


def get_tui_state(state_id: str) -> TuiStateView:
    try:
        return TUI_STATES[state_id]
    except KeyError as exc:
        raise ValueError(f"Unknown TUI state: {state_id}") from exc


def render_tui_state(state: TuiStateView) -> str:
    lines = [state.title, state.explanation, f"Action: {state.suggested_action}"]
    if state.command_palette_action_id:
        lines.append(f"Command: {state.command_palette_action_id}")
    if state.retry_action:
        lines.append(f"Retry: {state.retry_action}")
    return "\n".join(lines)


def state_has_safe_copy(state: TuiStateView) -> bool:
    text = render_tui_state(state).lower()
    banned = ("traceback", "attributeerror", "httpstatuserror", "stack trace")
    return not any(item in text for item in banned)


__all__ = ["STATE_IDS", "TUI_STATES", "TuiStateView", "get_tui_state", "render_tui_state", "state_has_safe_copy"]
