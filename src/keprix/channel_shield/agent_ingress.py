"""Agent OS ingress, memory, and outbound guards for Channel Shield."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from keprix.channel_shield.agent_policy import get_agent_policy
from keprix.channel_shield.agent_safe import BLOCKED_VERDICTS, policy_label_for
from keprix.channel_shield.store import get_channel_shield_store
from keprix.channel_shield.types import MessageStatus, PolicyLabel, Verdict

GuardAction = Literal[
    "prompt",
    "memory",
    "skill",
    "playbook",
    "tool",
    "outbound",
    "task",
]


@dataclass
class GuardDecision:
    allowed: bool
    reason: str
    policy_label: str | None = None
    message_id: str | None = None
    agent_safe_content: dict[str, Any] | None = None
    allowed_actions: list[str] = field(default_factory=list)
    requires_approval: bool = False
    incident_memory_only: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "policyLabel": self.policy_label,
            "messageId": self.message_id,
            "agentSafeContent": self.agent_safe_content,
            "allowedActions": list(self.allowed_actions),
            "requiresApproval": self.requires_approval,
            "incidentMemoryOnly": self.incident_memory_only,
        }


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _record_block(
    *,
    action: GuardAction,
    agent_id: str,
    message_id: str | None,
    reason: str,
    payload: dict[str, Any] | None = None,
) -> None:
    store = get_channel_shield_store()
    await store.record_agent_block(
        action=action,
        agent_id=agent_id,
        message_id=message_id,
        reason=reason,
        payload=payload or {},
    )


def _content_looks_like_raw_shielded(text: str) -> bool:
    lower = (text or "").lower()
    markers = (
        "eicar-standard-antivirus-test-file",
        "ignore previous instructions",
        "system prompt override",
        "powershell -enc",
    )
    return any(m in lower for m in markers)


async def guard_agent_ingress(
    *,
    action: GuardAction,
    agent_id: str = "assistant",
    message_id: str | None = None,
    content: str | None = None,
    tool_name: str | None = None,
    memory_kind: str | None = None,
    approval_granted: bool = False,
) -> GuardDecision:
    """Gate Agent OS surfaces before prompts, memory, tools, or outbound replies.

    Callers must pass ``message_id`` when acting on a shielded item. Raw content
    without a message_id is scanned for known-bad markers and blocked.
    """
    store = get_channel_shield_store()
    policy = get_agent_policy(agent_id)

    if message_id:
        message = await store.get_message(message_id)
        if message is None:
            decision = GuardDecision(False, "shielded message not found", message_id=message_id)
            await _record_block(
                action=action, agent_id=agent_id, message_id=message_id, reason=decision.reason
            )
            return decision

        label = policy_label_for(
            message.verdict or Verdict.ERROR.value,
            status=message.status,
        )
        agent_safe = dict(message.agent_safe_content or {})
        allowed_actions = list(agent_safe.get("allowedActions") or [])

        if message.status == MessageStatus.DESTROYED.value:
            decision = GuardDecision(
                False,
                "message destroyed",
                policy_label=PolicyLabel.DESTROYED.value,
                message_id=message_id,
            )
            await _record_block(
                action=action, agent_id=agent_id, message_id=message_id, reason=decision.reason
            )
            return decision

        verdict = message.verdict or ""
        blocked = verdict in BLOCKED_VERDICTS and message.status not in {
            MessageStatus.RELEASED.value,
            MessageStatus.DELIVERED.value,
        }

        if action == "memory":
            if blocked or label in {
                PolicyLabel.BLOCKED,
                PolicyLabel.NEEDS_HUMAN_REVIEW,
                PolicyLabel.SAFE_SUMMARY_ONLY,
            }:
                if (memory_kind or "").lower() in {"incident", "security_incident"}:
                    return GuardDecision(
                        True,
                        "incident memory allowed",
                        policy_label=label.value,
                        message_id=message_id,
                        agent_safe_content=agent_safe,
                        allowed_actions=allowed_actions,
                        incident_memory_only=True,
                    )
                decision = GuardDecision(
                    False,
                    "ordinary memory blocked for shielded content; use incident memory only",
                    policy_label=label.value,
                    message_id=message_id,
                    agent_safe_content=agent_safe,
                    incident_memory_only=True,
                )
                await _record_block(
                    action=action,
                    agent_id=agent_id,
                    message_id=message_id,
                    reason=decision.reason,
                )
                return decision

        if action in {"tool", "outbound", "skill", "playbook", "task"} and blocked:
            if action == "tool" and tool_name in {"channel_shield_release", "channel_shield_destroy"}:
                if tool_name == "channel_shield_destroy" and not policy.can_destroy:
                    decision = GuardDecision(
                        False,
                        "agent policy denies destroy",
                        policy_label=label.value,
                        message_id=message_id,
                        requires_approval=True,
                    )
                    await _record_block(
                        action=action,
                        agent_id=agent_id,
                        message_id=message_id,
                        reason=decision.reason,
                    )
                    return decision
                if not approval_granted and not (
                    tool_name == "channel_shield_release" and policy.can_release_after_approval
                ):
                    decision = GuardDecision(
                        False,
                        "release/destroy requires security approval",
                        policy_label=label.value,
                        message_id=message_id,
                        requires_approval=True,
                        agent_safe_content=agent_safe,
                        allowed_actions=allowed_actions,
                    )
                    await _record_block(
                        action=action,
                        agent_id=agent_id,
                        message_id=message_id,
                        reason=decision.reason,
                    )
                    return decision
                return GuardDecision(
                    True,
                    "approved high-risk shield tool",
                    policy_label=label.value,
                    message_id=message_id,
                    requires_approval=False,
                    agent_safe_content=agent_safe,
                )

            decision = GuardDecision(
                False,
                f"{action} blocked until human release (verdict={verdict})",
                policy_label=label.value,
                message_id=message_id,
                agent_safe_content=agent_safe,
                allowed_actions=allowed_actions,
                requires_approval=True,
            )
            await _record_block(
                action=action, agent_id=agent_id, message_id=message_id, reason=decision.reason
            )
            return decision

        if action == "prompt":
            if blocked:
                if not policy.can_view_safe_summary:
                    decision = GuardDecision(
                        False,
                        "agent policy denies safe summary view",
                        policy_label=label.value,
                        message_id=message_id,
                    )
                    await _record_block(
                        action=action,
                        agent_id=agent_id,
                        message_id=message_id,
                        reason=decision.reason,
                    )
                    return decision
                return GuardDecision(
                    True,
                    "use agentSafeContent only",
                    policy_label=label.value,
                    message_id=message_id,
                    agent_safe_content=agent_safe,
                    allowed_actions=allowed_actions,
                    requires_approval=True,
                )
            return GuardDecision(
                True,
                "clean content allowed",
                policy_label=label.value,
                message_id=message_id,
                agent_safe_content=agent_safe,
                allowed_actions=allowed_actions,
            )

        if action == "outbound":
            if blocked or not policy.can_contact_external_senders:
                decision = GuardDecision(
                    False,
                    "outbound reply blocked for shielded or policy-denied content",
                    policy_label=label.value,
                    message_id=message_id,
                    agent_safe_content=agent_safe,
                    requires_approval=True,
                )
                await _record_block(
                    action=action, agent_id=agent_id, message_id=message_id, reason=decision.reason
                )
                return decision

        return GuardDecision(
            True,
            "allowed",
            policy_label=label.value,
            message_id=message_id,
            agent_safe_content=agent_safe,
            allowed_actions=allowed_actions,
        )

    # No message_id: refuse raw malicious markers and credential bait.
    if content and _content_looks_like_raw_shielded(content):
        decision = GuardDecision(
            False,
            "raw suspicious content blocked without Channel Shield message id",
        )
        await _record_block(
            action=action, agent_id=agent_id, message_id=None, reason=decision.reason
        )
        return decision

    return GuardDecision(True, "no shield context")


async def guard_memory_write(
    content: str,
    *,
    agent_id: str = "assistant",
    message_id: str | None = None,
    memory_kind: str | None = None,
) -> GuardDecision:
    return await guard_agent_ingress(
        action="memory",
        agent_id=agent_id,
        message_id=message_id,
        content=content,
        memory_kind=memory_kind,
    )


async def guard_outbound_reply(
    content: str,
    *,
    agent_id: str = "assistant",
    message_id: str | None = None,
) -> GuardDecision:
    decision = await guard_agent_ingress(
        action="outbound",
        agent_id=agent_id,
        message_id=message_id,
        content=content,
    )
    if not decision.allowed:
        return decision
    lower = (content or "").lower()
    if message_id and any(
        token in lower
        for token in ("http://", "https://", "attachment", "password", "eicar")
    ):
        # Released prompts still must not quote raw payloads or open quarantined links.
        message = await get_channel_shield_store().get_message(message_id)
        if message and message.status == MessageStatus.RELEASED.value:
            safe = (message.agent_safe_content or {}).get("text") or ""
            if content.strip() and content.strip() not in safe and "eicar" in lower:
                blocked = GuardDecision(
                    False,
                    "outbound must not quote malicious payload fragments",
                    message_id=message_id,
                    policy_label=decision.policy_label,
                )
                await _record_block(
                    action="outbound",
                    agent_id=agent_id,
                    message_id=message_id,
                    reason=blocked.reason,
                )
                return blocked
    return decision


def new_approval_request(
    *,
    message_id: str,
    agent_id: str,
    action: str,
) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "messageId": message_id,
        "agentId": agent_id,
        "action": action,
        "status": "pending",
        "createdAt": _utcnow().isoformat(),
    }
