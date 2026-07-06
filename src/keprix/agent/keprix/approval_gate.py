"""Mandatory multi-channel approval gate."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from keprix.agent.keprix.config import get_mutation_config


@dataclass
class PendingApproval:
    request_id: str
    tool_name: str
    tool_code: str
    submitted_at: float
    channel_approvals: dict[str, bool] = field(default_factory=dict)
    channel_rejections: dict[str, str] = field(default_factory=dict)
    expires_at: float = field(default_factory=lambda: time.time() + 3600)

    def is_approved(self, required_channels: frozenset[str]) -> bool:
        return required_channels.issubset(self.channel_approvals.keys())

    def is_rejected(self) -> bool:
        return len(self.channel_rejections) > 0

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


_PENDING: dict[str, PendingApproval] = {}


def normalize_channel(channel: str) -> str:
    mapping = {
        "web": "web_ui",
        "webchat": "web_ui",
        "cli": "web_ui",
        "test": "web_ui",
        "admin": "web_ui",
    }
    return mapping.get(channel, channel)


def required_channels() -> frozenset[str]:
    config = get_mutation_config()
    return config.required_approval_channels


async def submit_for_approval(
    tool_name: str,
    tool_code: str,
    *,
    request_id: str | None = None,
    notifier: Callable[[PendingApproval], Awaitable[None]] | None = None,
) -> str:
    approval_id = request_id or str(uuid.uuid4())
    approval = PendingApproval(
        request_id=approval_id,
        tool_name=tool_name,
        tool_code=tool_code,
        submitted_at=time.time(),
    )
    _PENDING[approval_id] = approval
    if notifier is not None:
        await notifier(approval)
    return approval_id


async def record_decision(request_id: str, channel: str, approved: bool, reason: str = "") -> PendingApproval | None:
    approval = _PENDING.get(request_id)
    if approval is None:
        return None
    canonical = normalize_channel(channel)
    if approved:
        approval.channel_approvals[canonical] = True
    else:
        approval.channel_rejections[canonical] = reason or "rejected"
    return approval


def get_pending(request_id: str) -> PendingApproval | None:
    return _PENDING.get(request_id)


def clear_pending(request_id: str) -> None:
    _PENDING.pop(request_id, None)


async def wait_for_approval(request_id: str, timeout: float = 3600.0) -> bool:
    deadline = time.time() + timeout
    required = required_channels()
    while time.time() < deadline:
        approval = _PENDING.get(request_id)
        if approval is None:
            return False
        if approval.is_rejected():
            clear_pending(request_id)
            return False
        if approval.is_approved(required):
            clear_pending(request_id)
            return True
        if approval.is_expired():
            clear_pending(request_id)
            return False
        import asyncio

        await asyncio.sleep(0.05)
    return False
