"""Watch channel registration and renewal for Drive push (Prompt 649)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.document_vault.google.client import DriveClient
from keprix.document_vault.google.grants import new_verification_token
from keprix.document_vault.models import VaultError
from keprix.document_vault.store import DocumentVaultStore


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def webhook_public_url() -> str:
    base = (
        os.environ.get("KEPRIX_DOCUMENT_VAULT_GOOGLE_WEBHOOK_URL")
        or os.environ.get("API_PUBLIC_URL")
        or os.environ.get("KEPRIX_API_URL")
        or ""
    ).rstrip("/")
    if not base:
        return ""
    return f"{base}/api/document-vault/google/webhook"


class DriveWatchManager:
    def __init__(self, store: DocumentVaultStore, client: DriveClient) -> None:
        self.store = store
        self.client = client

    def register(self, workspace_id: str) -> dict[str, Any]:
        address = webhook_public_url()
        if not address.startswith("https://"):
            raise VaultError(
                "not_configured",
                "HTTPS webhook URL required for Drive push; use poll/manual sync locally",
            )
        conn = self.store.get_drive_connection(workspace_id)
        if not conn or not conn.get("connected"):
            raise VaultError("not_configured", "Google Drive not connected")
        page_token = str(conn.get("page_token") or self.client.start_page_token())
        plaintext, digest = new_verification_token()
        channel_id = f"keprix-dv-{workspace_id[:8]}-{uuid.uuid4().hex[:8]}"
        remote = self.client.watch_changes(
            channel_id=channel_id,
            address=address,
            token=plaintext,
            page_token=page_token,
        )
        expiry_ms = remote.get("expiration")
        expires_at = None
        if expiry_ms:
            try:
                expires_at = datetime.fromtimestamp(int(expiry_ms) / 1000, tz=timezone.utc).isoformat()
            except Exception:
                expires_at = (_utcnow() + timedelta(hours=20)).isoformat()
        self.store.update_drive_connection(
            workspace_id,
            channel_id=str(remote.get("id") or channel_id),
            resource_id=str(remote.get("resourceId") or ""),
            channel_expires_at=expires_at,
            verification_token_hash=digest,
            page_token=page_token,
        )
        return {
            "channel_id": remote.get("id") or channel_id,
            "resource_id": remote.get("resourceId"),
            "channel_expires_at": expires_at,
            "webhook_address": address,
        }

    def renew_if_needed(self, workspace_id: str, *, overlap_hours: float = 2.0) -> dict[str, Any]:
        conn = self.store.get_drive_connection(workspace_id)
        if not conn or not conn.get("channel_id"):
            return self.register(workspace_id)
        expires_raw = conn.get("channel_expires_at")
        if expires_raw:
            try:
                expires = datetime.fromisoformat(str(expires_raw).replace("Z", "+00:00"))
            except ValueError:
                expires = _utcnow()
            if expires - _utcnow() > timedelta(hours=overlap_hours):
                return {
                    "renewed": False,
                    "channel_id": conn.get("channel_id"),
                    "channel_expires_at": expires_raw,
                }
        old_channel = str(conn.get("channel_id") or "")
        old_resource = str(conn.get("resource_id") or "")
        result = self.register(workspace_id)
        if old_channel and old_resource:
            try:
                self.client.stop_channel(old_channel, old_resource)
            except VaultError:
                pass
        result["renewed"] = True
        result["stopped_previous"] = bool(old_channel)
        return result

    def stop(self, workspace_id: str) -> None:
        conn = self.store.get_drive_connection(workspace_id)
        if not conn:
            return
        channel_id = conn.get("channel_id")
        resource_id = conn.get("resource_id")
        if channel_id and resource_id:
            try:
                self.client.stop_channel(str(channel_id), str(resource_id))
            except VaultError:
                pass
        self.store.update_drive_connection(
            workspace_id,
            channel_id=None,
            resource_id=None,
            channel_expires_at=None,
            verification_token_hash="",
        )


__all__ = ["DriveWatchManager", "webhook_public_url"]
