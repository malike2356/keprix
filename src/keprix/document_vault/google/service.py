"""High-level Google Drive sync service for Document Vault (Prompt 649)."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlencode

from keprix.document_vault.flags import load_flags
from keprix.document_vault.google.client import DriveClient, DriveTransport, FakeDriveTransport
from keprix.document_vault.google.grants import (
    DriveGrant,
    decrypt_grant,
    encrypt_grant,
    redact_mapping,
    verify_channel_token,
)
from keprix.document_vault.google.reconcile import DriveReconciler
from keprix.document_vault.google.scopes import consent_copy, scopes_for_mode, validate_mode
from keprix.document_vault.google.watch import DriveWatchManager, webhook_public_url
from keprix.document_vault.models import VaultError
from keprix.document_vault.service import DocumentVaultService, get_document_vault_service
from keprix.document_vault.store import DocumentVaultStore, get_document_vault_store


def google_sync_enabled() -> bool:
    flags = load_flags()
    return bool(flags.enabled and flags.google_sync)


def shared_drives_allowed() -> bool:
    return False  # Gated until flags, corpora, permissions, and tests exist.


class GoogleDriveVaultService:
    def __init__(
        self,
        store: DocumentVaultStore | None = None,
        vault: DocumentVaultService | None = None,
        transport: DriveTransport | None = None,
    ) -> None:
        self.store = store or get_document_vault_store()
        self.vault = vault or get_document_vault_service(store=self.store)
        self._transport = transport

    def status(self, workspace_id: str) -> dict[str, Any]:
        if not load_flags().enabled:
            return {
                "ok": False,
                "error_code": "not_configured",
                "message": "Document Vault disabled",
                "google_sync_enabled": False,
            }
        conn = self.store.get_drive_connection(workspace_id)
        if not conn or not conn.get("connected"):
            return {
                "ok": True,
                "connected": False,
                "google_sync_enabled": google_sync_enabled(),
                "shared_drives_enabled": False,
                "webhook_configured": webhook_public_url().startswith("https://"),
                "modes": ["outbound_only", "inbound_only", "two_way"],
                "message": "Google Drive not connected; local vault remains available",
            }
        public = redact_mapping(
            {
                "ok": True,
                "connected": True,
                "mode": conn.get("mode"),
                "account_email": conn.get("account_email"),
                "scopes": conn.get("scopes") or [],
                "root_folder_id": conn.get("root_folder_id"),
                "root_folder_name": conn.get("root_folder_name"),
                "page_token_set": bool(conn.get("page_token")),
                "channel_id": conn.get("channel_id"),
                "channel_expires_at": conn.get("channel_expires_at"),
                "last_sync_at": conn.get("last_sync_at"),
                "last_error": conn.get("last_error"),
                "shared_drives_enabled": False,
                "google_sync_enabled": google_sync_enabled(),
                "webhook_configured": webhook_public_url().startswith("https://"),
                "consent": consent_copy(str(conn.get("mode") or "outbound_only")),
            }
        )
        return public

    def begin_connect(
        self,
        workspace_id: str,
        *,
        user_id: str,
        mode: str = "outbound_only",
        redirect_uri: str | None = None,
    ) -> dict[str, Any]:
        if not google_sync_enabled():
            raise VaultError("not_configured", "Enable KEPRIX_DOCUMENT_VAULT_GOOGLE_SYNC")
        mode_key = validate_mode(mode)
        scopes = scopes_for_mode(mode_key)
        client_id = (
            os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
            or os.environ.get("KEPRIX_GOOGLE_CLIENT_ID")
            or ""
        ).strip()
        if not client_id:
            raise VaultError("not_configured", "Google OAuth client id missing")
        redirect = (
            redirect_uri
            or os.environ.get("KEPRIX_DOCUMENT_VAULT_GOOGLE_REDIRECT_URI")
            or os.environ.get("GOOGLE_OAUTH_REDIRECT_URI")
            or "http://localhost:3333/api/document-vault/google/callback"
        )
        params = urlencode(
            {
                "client_id": client_id,
                "redirect_uri": redirect,
                "response_type": "code",
                "access_type": "offline",
                "include_granted_scopes": "true",
                "prompt": "consent",
                "scope": " ".join(scopes),
                "state": f"{workspace_id}:{user_id}:{mode_key}",
            }
        )
        self.store.upsert_drive_connection(
            workspace_id,
            user_id=user_id,
            mode=mode_key,
            scopes=scopes,
            connected=False,
            verification_token_hash="",
        )
        return {
            "auth_url": f"https://accounts.google.com/o/oauth2/v2/auth?{params}",
            "mode": mode_key,
            "scopes": scopes,
            "consent": consent_copy(mode_key),
            "redirect_uri": redirect,
        }

    def complete_connect(
        self,
        workspace_id: str,
        *,
        user_id: str,
        access_token: str,
        refresh_token: str = "",
        account_email: str | None = None,
        scopes: list[str] | None = None,
        mode: str | None = None,
        expires_at: str | None = None,
    ) -> dict[str, Any]:
        if not access_token and not refresh_token:
            raise VaultError("not_configured", "OAuth tokens missing")
        conn = self.store.get_drive_connection(workspace_id)
        mode_key = validate_mode(mode or (conn or {}).get("mode") or "outbound_only")
        grant = DriveGrant(
            access_token=access_token,
            refresh_token=refresh_token,
            account_email=account_email,
            scopes=scopes or scopes_for_mode(mode_key),
            expires_at=expires_at,
        )
        ciphertext = encrypt_grant(grant)
        client = self._client_from_grant(grant)
        page_token = client.start_page_token()
        self.store.upsert_drive_connection(
            workspace_id,
            user_id=user_id,
            mode=mode_key,
            scopes=grant.scopes,
            account_email=account_email,
            grant_ciphertext=ciphertext,
            page_token=page_token,
            connected=True,
            last_error=None,
        )
        return self.status(workspace_id)

    def configure_root(
        self,
        workspace_id: str,
        *,
        root_folder_id: str,
        root_folder_name: str | None = None,
        mode: str | None = None,
        enable_shared_drives: bool = False,
    ) -> dict[str, Any]:
        if enable_shared_drives:
            raise VaultError(
                "not_configured",
                "Shared Drives are gated until flags, corpora, permissions, and tests exist",
            )
        fields: dict[str, Any] = {
            "root_folder_id": root_folder_id,
            "root_folder_name": root_folder_name or root_folder_id,
            "shared_drives_enabled": False,
        }
        if mode:
            fields["mode"] = validate_mode(mode)
        self.store.update_drive_connection(workspace_id, **fields)
        return self.status(workspace_id)

    def disconnect(self, workspace_id: str) -> dict[str, Any]:
        try:
            client = self._client_for_workspace(workspace_id)
            DriveWatchManager(self.store, client).stop(workspace_id)
        except VaultError:
            pass
        self.store.delete_drive_connection(workspace_id)
        return {"ok": True, "connected": False}

    def sync_now(
        self,
        workspace_id: str,
        *,
        source: str = "manual",
        actor_id: str | None = None,
        direction: str = "inbound",
        item_id: str | None = None,
    ) -> dict[str, Any]:
        if not google_sync_enabled():
            raise VaultError("not_configured", "Google Drive sync flag off")
        client = self._client_for_workspace(workspace_id)
        reconciler = DriveReconciler(self.store, self.vault, client)
        if direction == "outbound":
            if not item_id:
                raise VaultError("unsupported_kind", "item_id required for outbound push")
            return reconciler.push_item(workspace_id, item_id, actor_id=actor_id)
        result = reconciler.reconcile_inbound(
            workspace_id,
            source=source if source in {"poll", "webhook", "manual"} else "manual",  # type: ignore[arg-type]
            actor_id=actor_id,
        )
        return result.as_dict()

    def handle_webhook(
        self,
        *,
        channel_id: str,
        resource_id: str,
        channel_token: str,
        message_number: str | None = None,
        resource_state: str | None = None,
    ) -> dict[str, Any]:
        # Empty / sync notifications still wake reconciliation via page token.
        workspace_id = self._workspace_for_channel(channel_id, resource_id)
        conn = self.store.get_drive_connection(workspace_id)
        if not conn:
            raise VaultError("not_found", "unknown channel")
        if not verify_channel_token(channel_token, str(conn.get("verification_token_hash") or "")):
            raise VaultError("forbidden", "invalid channel verification token")
        notification_id = f"{channel_id}:{message_number or resource_state or 'wake'}"
        client = self._client_for_workspace(workspace_id)
        reconciler = DriveReconciler(self.store, self.vault, client)
        result = reconciler.reconcile_inbound(
            workspace_id,
            source="webhook",
            notification_id=notification_id,
        )
        return result.as_dict()

    def renew_watch(self, workspace_id: str) -> dict[str, Any]:
        client = self._client_for_workspace(workspace_id)
        return DriveWatchManager(self.store, client).renew_if_needed(workspace_id)

    def list_conflicts(self, workspace_id: str) -> dict[str, Any]:
        return {"workspace_id": workspace_id, "conflicts": self.store.list_conflicts(workspace_id)}

    def resolve_conflict(
        self,
        workspace_id: str,
        item_id: str,
        *,
        choice: str,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        mapping = self.store.get_provider_mapping_for_item(workspace_id, item_id, "google_drive")
        if not mapping or not mapping.get("conflict_state"):
            raise VaultError("not_found", "no conflict for item")
        meta = dict(mapping.get("metadata") or {})
        conflict_item_id = meta.get("conflict_item_id")
        if choice == "keep_local":
            if conflict_item_id:
                self.store.trash(workspace_id, str(conflict_item_id), actor_id=actor_id)
            self.store.upsert_provider_mapping(
                workspace_id,
                item_id,
                provider="google_drive",
                provider_item_id=str(mapping["provider_item_id"]),
                provider_revision=str(mapping.get("provider_revision") or ""),
                content_authority="workspace",
                conflict_state=None,
                metadata={k: v for k, v in meta.items() if k != "conflict_item_id"},
            )
        elif choice == "keep_remote":
            self.store.trash(workspace_id, item_id, actor_id=actor_id)
            if conflict_item_id:
                self.store.upsert_provider_mapping(
                    workspace_id,
                    str(conflict_item_id),
                    provider="google_drive",
                    provider_item_id=str(mapping["provider_item_id"]).split(":conflict:")[0],
                    provider_revision=str(meta.get("remote_revision") or ""),
                    content_authority="google",
                    conflict_state=None,
                    metadata={},
                )
        elif choice == "keep_both":
            self.store.upsert_provider_mapping(
                workspace_id,
                item_id,
                provider="google_drive",
                provider_item_id=str(mapping["provider_item_id"]),
                provider_revision=str(mapping.get("provider_revision") or ""),
                content_authority="workspace",
                conflict_state="resolved_keep_both",
                metadata=meta,
            )
        else:
            raise VaultError("unsupported_kind", f"unknown choice {choice}")
        return {"ok": True, "choice": choice, "item_id": item_id}

    def refresh_grant(self, workspace_id: str) -> dict[str, Any]:
        grant = self._grant_for_workspace(workspace_id)
        client = self._client_from_grant(grant)
        client.refresh_access_token(
            client_id=os.environ.get("GOOGLE_OAUTH_CLIENT_ID", ""),
            client_secret=os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", ""),
        )
        conn = self.store.get_drive_connection(workspace_id) or {}
        self.store.update_drive_connection(
            workspace_id,
            grant_ciphertext=encrypt_grant(client.grant),
            account_email=conn.get("account_email"),
        )
        return {"ok": True, "refreshed": True}

    def _grant_for_workspace(self, workspace_id: str) -> DriveGrant:
        conn = self.store.get_drive_connection(workspace_id)
        if not conn or not conn.get("grant_ciphertext"):
            raise VaultError("not_configured", "Google Drive grant missing")
        return decrypt_grant(str(conn["grant_ciphertext"]))

    def _client_from_grant(self, grant: DriveGrant) -> DriveClient:
        return DriveClient(grant, transport=self._transport or FakeDriveTransport())

    def _client_for_workspace(self, workspace_id: str) -> DriveClient:
        return self._client_from_grant(self._grant_for_workspace(workspace_id))

    def _workspace_for_channel(self, channel_id: str, resource_id: str) -> str:
        # Linear scan is fine for CE; PG deployments keep few connections per host.
        # Store has no index helper yet; use SQL.
        with self.store._lock:
            row = self.store._fetchone(
                """
                SELECT workspace_id FROM document_vault_drive_connections
                WHERE channel_id = ? AND (resource_id = ? OR ? = '')
                """,
                (channel_id, resource_id, resource_id),
            )
        if not row:
            raise VaultError("not_found", "channel not registered")
        return str(row["workspace_id"])


__all__ = ["GoogleDriveVaultService", "google_sync_enabled", "shared_drives_allowed"]
