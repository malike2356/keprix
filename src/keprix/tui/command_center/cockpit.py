"""Workspace cockpit model and renderer."""

from __future__ import annotations

from dataclasses import dataclass, field

from keprix.tui.client import ModelItem, RegistryItem, SessionItem
from keprix.tui.command_center.actions import CommandCenterAction
from keprix.tui.command_center.registry import runtime_actions
from keprix.tui.hardening import assert_no_traceback


@dataclass(frozen=True)
class WorkspaceCockpitState:
    active_session_id: str = ""
    active_session_title: str = "New conversation"
    selected_model: str = ""
    transport_mode: str = "unknown"
    backend_health: str = "offline"
    queue_depth: int = 0
    skills: tuple[RegistryItem, ...] = ()
    plugins: tuple[RegistryItem, ...] = ()
    recent_sessions: tuple[SessionItem, ...] = ()
    setup_warning: str = ""
    quick_actions: tuple[CommandCenterAction, ...] = field(default_factory=lambda: tuple(runtime_actions()))


def build_cockpit_state(
    *,
    session_id: str = "",
    sessions: list[SessionItem] | None = None,
    model: str = "",
    models: list[ModelItem] | None = None,
    transport_mode: str = "unknown",
    connected: bool = False,
    queue_depth: int = 0,
    skills: list[RegistryItem] | None = None,
    plugins: list[RegistryItem] | None = None,
    setup_required: bool = False,
) -> WorkspaceCockpitState:
    session_rows = list(sessions or [])
    active = next((item for item in session_rows if item.id == session_id), None)
    selected_model = model or (models[0].id if models else "")
    return WorkspaceCockpitState(
        active_session_id=session_id,
        active_session_title=active.title if active else "New conversation",
        selected_model=selected_model or "-",
        transport_mode=transport_mode,
        backend_health="online" if connected else "offline",
        queue_depth=max(0, queue_depth),
        skills=tuple(skills or ()),
        plugins=tuple(plugins or ()),
        recent_sessions=tuple(session_rows[:5]),
        setup_warning="Provider setup required. Use /setup." if setup_required else "",
    )


def render_workspace_cockpit(state: WorkspaceCockpitState) -> str:
    lines = [
        "Keprix Command Center",
        f"Session: {state.active_session_title} ({state.active_session_id or 'none'})",
        f"Model: {state.selected_model}",
        f"Runtime: {state.transport_mode} | Backend: {state.backend_health}",
        f"Queue: {state.queue_depth}",
    ]
    if state.setup_warning:
        lines.append(f"Setup: {state.setup_warning}")
    lines.append("")
    lines.append("Recent sessions")
    if state.recent_sessions:
        lines.extend(f"- {item.title[:42]} ({item.last_active or item.id})" for item in state.recent_sessions[:5])
    else:
        lines.append("- No recent sessions")
    lines.append("")
    lines.append("Skills")
    lines.append(_item_summary([item.name for item in state.skills], empty="No skills loaded"))
    lines.append("Plugins")
    lines.append(_item_summary([item.name for item in state.plugins], empty="No plugins loaded"))
    lines.append("")
    lines.append("Quick actions")
    lines.extend(f"- {action.title}: {action.description}" for action in state.quick_actions[:5])
    rendered = "\n".join(lines)
    assert_no_traceback(rendered)
    return rendered


def _item_summary(items: list[str], *, empty: str) -> str:
    if not items:
        return f"- {empty}"
    shown = ", ".join(items[:5])
    suffix = f" (+{len(items) - 5})" if len(items) > 5 else ""
    return f"- {shown}{suffix}"


__all__ = ["WorkspaceCockpitState", "build_cockpit_state", "render_workspace_cockpit"]
