"""Audience execution context (Prompt 630)."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from keprix.customer_concierge.audience.tool_policy import (
    assert_tool_allowed,
    is_customer_concierge_tool_allowed,
)


@dataclass(frozen=True)
class AudiencePrincipalContext:
    workspace_id: str
    persona_id: str
    session_id: str
    identity_id: str
    channel: str
    session_mode: str = "public"

    @property
    def workspace_member(self) -> bool:
        return False

    @property
    def actor_type(self) -> str:
        return "audience"


_ctx: ContextVar[AudiencePrincipalContext | None] = ContextVar("audience_principal", default=None)


def set_audience_context(ctx: AudiencePrincipalContext) -> None:
    _ctx.set(ctx)


def clear_audience_context() -> None:
    _ctx.set(None)


def get_audience_context() -> AudiencePrincipalContext | None:
    return _ctx.get()


def require_audience_context() -> AudiencePrincipalContext:
    ctx = _ctx.get()
    if ctx is None:
        raise PermissionError("audience_context_required")
    return ctx


def gate_tool_for_current_audience(tool_name: str) -> dict[str, Any]:
    """Deny-by-default tool gate when an audience principal is active."""
    ctx = get_audience_context()
    if ctx is None:
        # No audience context: not an external visitor turn
        return {"ok": True, "audience": False}
    allowed = is_customer_concierge_tool_allowed(tool_name)
    if not allowed:
        try:
            from keprix.customer_concierge.audience.store import get_audience_store

            get_audience_store().append_audit(
                workspace_id=ctx.workspace_id,
                session_id=ctx.session_id,
                identity_id=ctx.identity_id,
                event_type="tool_policy.audience_tool_denied",
                actor_type="system",
                detail={"tool": tool_name},
            )
        except Exception:
            pass
        return {
            "ok": False,
            "error_code": "audience_tool_denied",
            "tool": tool_name,
            "workspaceMember": False,
        }
    return {"ok": True, "audience": True, "tool": tool_name}


def execute_audience_tool(tool_name: str, handler: Any, *args: Any, **kwargs: Any) -> Any:
    """Run a tool only if allowlisted for the current audience principal."""
    assert_tool_allowed(tool_name)
    require_audience_context()
    return handler(*args, **kwargs)
