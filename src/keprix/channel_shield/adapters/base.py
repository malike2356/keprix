"""Adapter protocol for Channel Shield ingress/egress."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from keprix.channel_shield.types import ShieldEnvelope


class ChannelAdapter(ABC):
    channel: str

    @abstractmethod
    def authenticate_ingress(self, headers: dict[str, str], body: bytes) -> dict[str, Any]:
        """Validate ingress authenticity. Return auth_signals; raise on hard fail."""

    @abstractmethod
    def ingest(
        self,
        payload: dict[str, Any] | bytes,
        *,
        protection_id: str,
        auth_signals: dict[str, Any] | None = None,
    ) -> tuple[ShieldEnvelope, bytes | None, dict[str, bytes]]:
        """
        Parse inbound into ShieldEnvelope.
        Returns (envelope, raw_bytes, attachment_bytes_by_id).
        """

    @abstractmethod
    async def deliver(self, envelope: ShieldEnvelope, message_id: str) -> dict[str, Any]:
        """Deliver clean message to destination on this channel."""

    @abstractmethod
    async def notify_safe_summary(
        self, envelope: ShieldEnvelope, message_id: str, summary: str
    ) -> dict[str, Any]:
        """Send safe summary without live malicious payload."""

    async def suppress_original(self, envelope: ShieldEnvelope) -> dict[str, Any]:
        """Optional: delete/hide original on platforms that allow it."""
        return {"suppressed": False, "reason": "not supported"}

    async def health(self) -> dict[str, Any]:
        return {"channel": self.channel, "ok": True, "mode": "local"}
