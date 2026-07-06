"""Human approval hooks for typed agents."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from keprix.agent.keprix.approval_gate import submit_for_approval
from keprix.browser.safety import requires_approval as browser_requires_approval


class ApprovalAction(StrEnum):
    TOOL_EXECUTION = "tool_execution"
    OUTPUT_PUBLICATION = "output_publication"
    BROWSER_SUBMIT = "browser_submit"
    EMAIL_SEND = "email_send"
    FILE_WRITE = "file_write"
    PAYMENT_CHANGE = "payment_change"


_ACTION_TO_BROWSER = {
    ApprovalAction.BROWSER_SUBMIT: "submit",
    ApprovalAction.PAYMENT_CHANGE: "purchase",
}


DEFAULT_APPROVAL_ACTIONS = frozenset(
    {
        ApprovalAction.TOOL_EXECUTION,
        ApprovalAction.OUTPUT_PUBLICATION,
        ApprovalAction.BROWSER_SUBMIT,
        ApprovalAction.EMAIL_SEND,
        ApprovalAction.FILE_WRITE,
        ApprovalAction.PAYMENT_CHANGE,
    }
)


def approval_required(action: str | ApprovalAction) -> bool:
    normalized = ApprovalAction(action) if action in ApprovalAction._value2member_map_ else action
    if normalized in DEFAULT_APPROVAL_ACTIONS:
        return True
    browser_action = _ACTION_TO_BROWSER.get(normalized)  # type: ignore[arg-type]
    if browser_action:
        return browser_requires_approval(browser_action)
    return False


async def request_approval(
    *,
    action: str | ApprovalAction,
    summary: str,
    request_id: str | None = None,
    auto_approve: bool = False,
) -> dict[str, Any]:
    if not approval_required(action):
        return {"required": False, "approved": True, "action": str(action)}
    if auto_approve:
        return {"required": True, "approved": True, "action": str(action), "auto_approved": True}
    approval_id = await submit_for_approval(
        tool_name=str(action),
        tool_code=summary,
        request_id=request_id,
    )
    return {
        "required": True,
        "approved": False,
        "action": str(action),
        "approval_id": approval_id,
    }
