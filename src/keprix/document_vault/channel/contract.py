"""Reusable channel attachment and platform capability contract (Prompt 651)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Platforms that may carry files through the shared vault attachment contract.
CHANNEL_MATRIX: dict[str, dict[str, Any]] = {
    "telegram": {"files": True, "max_attach_bytes": 20 * 1024 * 1024, "slash": True},
    "slack": {"files": True, "max_attach_bytes": 20 * 1024 * 1024, "slash": True},
    "teams": {"files": True, "max_attach_bytes": 15 * 1024 * 1024, "slash": True},
    "whatsapp": {"files": True, "max_attach_bytes": 16 * 1024 * 1024, "slash": True},
    "discord": {"files": True, "max_attach_bytes": 25 * 1024 * 1024, "slash": True},
    "email": {"files": True, "max_attach_bytes": 10 * 1024 * 1024, "slash": False},
    "sms": {"files": False, "max_attach_bytes": 0, "slash": False},
    "web": {"files": True, "max_attach_bytes": 25 * 1024 * 1024, "slash": True},
}


def channel_supports_files(platform: str) -> bool:
    row = CHANNEL_MATRIX.get(str(platform or "").strip().lower())
    return bool(row and row.get("files"))


def channel_max_attach_bytes(platform: str) -> int:
    row = CHANNEL_MATRIX.get(str(platform or "").strip().lower()) or {}
    return int(row.get("max_attach_bytes") or 0)


@dataclass
class ChannelAttachment:
    """Normalized inbound/outbound attachment for any gateway platform."""

    platform: str
    channel_user_id: str
    event_id: str
    filename: str
    data: bytes = b""
    declared_mime: str = ""
    caption: str = ""
    parent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def byte_size(self) -> int:
        return len(self.data or b"")


@dataclass
class ChannelReceipt:
    ok: bool
    message: str
    item_id: str | None = None
    job_id: str | None = None
    deduplicated: bool = False
    data: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "CHANNEL_MATRIX",
    "ChannelAttachment",
    "ChannelReceipt",
    "channel_max_attach_bytes",
    "channel_supports_files",
]
