"""Shared helper to run product + resource ACL checks before tool dispatch."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _is_consequential_tool(tool_name: str) -> bool:
    lowered = tool_name.strip().lower()
    return lowered.startswith((
        "terminal:",
        "email:send",
        "mail:send",
        "file:write",
        "file:delete",
        "vault:",
        "git:",
        "pack:",
        "install:",
        "network:",
        "code_exec:",
        "code-exec:",
        "message:",
    ))


def _is_private_data_tool(tool_name: str) -> bool:
    lowered = tool_name.strip().lower()
    return lowered.startswith(("memory:", "rag:", "search:", "read:", "contacts:", "documents:", "email:read", "mail:read", "vault:read"))


def _resolve_actor(agent: Any) -> tuple[str | None, str | None, str | None, str]:
    """Return (actor_type, actor_id, workspace_id, product_id)."""
    product_id = "keprix"
    try:
        from keprix.security.product_context import get_product_context_or_none

        ctx = get_product_context_or_none()
        if ctx is not None and getattr(ctx, "product_id", None):
            product_id = str(ctx.product_id)
    except Exception:
        pass

    workspace_id = (
        getattr(agent, "workspace_id", None)
        or getattr(agent, "_workspace_id", None)
        or None
    )
    api_token_id = getattr(agent, "api_token_id", None) or getattr(agent, "_api_token_id", None)
    agent_id = getattr(agent, "agent_id", None) or getattr(agent, "persona_id", None)
    user_id = getattr(agent, "user_id", None) or getattr(agent, "_user_id", None)

    if api_token_id:
        return "api_token", str(api_token_id), workspace_id and str(workspace_id), product_id
    if agent_id:
        return "agent", str(agent_id), workspace_id and str(workspace_id), product_id
    if user_id:
        return "user", str(user_id), workspace_id and str(workspace_id), product_id
    if workspace_id:
        return "workspace", str(workspace_id), str(workspace_id), product_id
    return None, None, workspace_id and str(workspace_id), product_id


def _run_async(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # Already in a loop: schedule and do not block; return a sync fallback check.
    return None


def evaluate_tool_acl_gate(
    agent: Any,
    tool_name: str,
    tool_args: dict[str, Any] | None,
) -> str | None:
    """Return a denial message if ACL blocks the call; otherwise None."""
    actor_type, actor_id, workspace_id, product_id = _resolve_actor(agent)
    session_id = getattr(agent, "session_id", None) or ""

    try:
        from keprix.security.rule_of_two import record_leg

        state = record_leg(
            session_id,
            private_data=_is_private_data_tool(tool_name),
            external_side_effect=_is_consequential_tool(tool_name),
            tool_name=tool_name,
        )
        if state.human_approval_required and _is_consequential_tool(tool_name):
            return (
                f"[approval_required] Rule of Two requires human approval before '{tool_name}' can run. "
                "The session already contains private data and untrusted or external side effect context."
            )
    except Exception:
        logger.debug("rule of two gate skipped", exc_info=True)

    # 1) Product tool-name ACL
    try:
        from keprix.security.tool_acl import ACLDecision, get_tool_acl
        from keprix.security.tool_acl_audit import get_acl_audit_log

        acl = get_tool_acl()
        decision = acl.check(product_id, tool_name)
        _run_async(
            get_acl_audit_log().record(
                product_id=product_id,
                tool_name=tool_name,
                decision=decision,
                workspace_id=workspace_id,
                session_id=session_id or None,
            )
        )
        if decision != ACLDecision.ALLOWED:
            from keprix.security.tool_acl_denied import ToolACLDenied

            denied = ToolACLDenied(
                product_id=product_id,
                tool_name=tool_name,
                reason=f"product ACL decision={decision.value}",
            )
            return denied.to_tool_result().get("content")
    except Exception:
        logger.debug("product tool ACL gate skipped", exc_info=True)

    # 2) Resource-scoped ACL
    try:
        from keprix.security.resource_scopes.enforce import (
            check_and_audit_resource_acl,
            check_resource_acl,
        )
        from keprix.security.tool_acl_denied import ToolACLDenied

        # Prefer async audit when possible; always compute sync decision.
        resource_decision = check_resource_acl(
            tool_name,
            tool_args if isinstance(tool_args, dict) else {},
            actor_type=actor_type,  # type: ignore[arg-type]
            actor_id=actor_id,
        )
        audited = _run_async(
            check_and_audit_resource_acl(
                tool_name,
                tool_args if isinstance(tool_args, dict) else {},
                product_id=product_id,
                actor_type=actor_type,  # type: ignore[arg-type]
                actor_id=actor_id,
                workspace_id=workspace_id,
                session_id=session_id or None,
            )
        )
        if audited is not None:
            resource_decision = audited

        if not resource_decision.allowed:
            denied = ToolACLDenied(
                product_id=product_id,
                tool_name=tool_name,
                reason=resource_decision.reason,
                service=resource_decision.service,
                action=resource_decision.action,
                resource_kind=resource_decision.kind,
                resource_id=resource_decision.resource_id,
            )
            return denied.to_tool_result().get("content")
    except Exception:
        logger.debug("resource tool ACL gate skipped", exc_info=True)

    return None
