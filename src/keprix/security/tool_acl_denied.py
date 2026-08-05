"""ToolACLDenied: structured exception returned when a tool call is blocked by ACL.

The exception carries enough information for the agent runtime to build a
tool_acl_denied response without crashing the conversation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ToolACLDenied(Exception):
    """Raised by ToolACL.check() when a tool call is not allowed.

    The agent runtime MUST catch this and return a structured error to the
    model rather than propagating it as an unhandled exception.  Conversation
    continues; the model sees a tool result with ``role="tool"`` and
    ``content`` describing the denial.
    """
    product_id: str
    tool_name: str
    reason: str
    service: str | None = None
    action: str | None = None
    resource_kind: str | None = None
    resource_id: str | None = None

    def __str__(self) -> str:
        return (
            f"Tool ACL denied: product={self.product_id!r} "
            f"tool={self.tool_name!r} reason={self.reason}"
        )

    def to_tool_result(self, tool_call_id: str = "") -> dict:
        """Return an OpenAI-compatible tool result dict for model consumption."""
        detail = self.reason
        if self.service or self.resource_id:
            detail = (
                f"{self.reason} "
                f"(service={self.service}, action={self.action}, "
                f"kind={self.resource_kind}, resource={self.resource_id})"
            )
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": (
                f"[tool_acl_denied] The tool '{self.tool_name}' is not available "
                f"for product '{self.product_id}'. Reason: {detail}. "
                "Use a different approach that does not require this tool, "
                "or ask the operator to approve the exact resource."
            ),
            "_keprix_acl_denied": True,
            "_denied_tool": self.tool_name,
            "_denied_product": self.product_id,
            "_denied_service": self.service,
            "_denied_action": self.action,
            "_denied_resource_kind": self.resource_kind,
            "_denied_resource_id": self.resource_id,
        }
