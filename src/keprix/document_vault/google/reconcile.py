"""Single reconciliation engine for Drive poll and push notifications (649)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from keprix.document_vault.google.client import DriveClient
from keprix.document_vault.google.export_mime import vault_kind_for_google_mime
from keprix.document_vault.models import VaultError, sanitize_name
from keprix.document_vault.service import DocumentVaultService
from keprix.document_vault.store import DocumentVaultStore

ReconcileSource = Literal["poll", "webhook", "manual", "outbound"]


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class ReconcileResult:
    workspace_id: str
    source: str
    applied: int = 0
    conflicts: int = 0
    skipped: int = 0
    pages: int = 0
    new_page_token: str | None = None
    errors: list[str] = field(default_factory=list)
    duplicate_notification: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "source": self.source,
            "applied": self.applied,
            "conflicts": self.conflicts,
            "skipped": self.skipped,
            "pages": self.pages,
            "new_page_token": self.new_page_token,
            "errors": list(self.errors),
            "duplicate_notification": self.duplicate_notification,
        }


class DriveReconciler:
    """Inbound changes.list + outbound push share this engine."""

    def __init__(
        self,
        store: DocumentVaultStore,
        service: DocumentVaultService,
        client: DriveClient,
    ) -> None:
        self.store = store
        self.service = service
        self.client = client

    def reconcile_inbound(
        self,
        workspace_id: str,
        *,
        source: ReconcileSource = "manual",
        actor_id: str | None = None,
        notification_id: str | None = None,
        max_pages: int = 50,
    ) -> ReconcileResult:
        conn = self.store.get_drive_connection(workspace_id)
        if not conn or not conn.get("connected"):
            raise VaultError("not_configured", "Google Drive not connected for this workspace")
        mode = str(conn.get("mode") or "two_way")
        if mode == "outbound_only":
            raise VaultError("forbidden", "inbound sync disabled for outbound_only mode")

        result = ReconcileResult(workspace_id=workspace_id, source=source)
        if notification_id and self.store.seen_drive_notification(workspace_id, notification_id):
            result.duplicate_notification = True
            result.skipped = 1
            return result
        if notification_id:
            self.store.record_drive_notification(workspace_id, notification_id)

        page_token = str(conn.get("page_token") or "") or self.client.start_page_token()
        pages = 0
        while pages < max_pages:
            pages += 1
            result.pages = pages
            try:
                payload = self.client.list_changes(page_token, page_size=100)
            except VaultError as exc:
                result.errors.append(exc.message)
                self.store.update_drive_connection(workspace_id, last_error=exc.message)
                break

            for change in payload.get("changes") or []:
                try:
                    outcome = self._apply_change(workspace_id, change, actor_id=actor_id)
                    if outcome == "conflict":
                        result.conflicts += 1
                    elif outcome == "applied":
                        result.applied += 1
                    else:
                        result.skipped += 1
                except VaultError as exc:
                    result.errors.append(exc.message)

            next_token = payload.get("nextPageToken")
            new_start = payload.get("newStartPageToken")
            if next_token:
                page_token = str(next_token)
                continue
            if new_start:
                page_token = str(new_start)
            result.new_page_token = page_token
            break

        self.store.update_drive_connection(
            workspace_id,
            page_token=result.new_page_token or page_token,
            last_sync_at=_utcnow(),
            last_error="; ".join(result.errors) if result.errors else None,
        )
        self.store.enqueue_job(
            workspace_id,
            "google_drive_reconcile",
            idempotency_key=f"reconcile:{workspace_id}:{source}:{result.new_page_token or page_token}",
            payload=result.as_dict(),
        )
        return result

    def _apply_change(
        self,
        workspace_id: str,
        change: dict[str, Any],
        *,
        actor_id: str | None,
    ) -> str:
        file_id = str(change.get("fileId") or (change.get("file") or {}).get("id") or "")
        if not file_id:
            return "skipped"
        removed = bool(change.get("removed"))
        mapping = self.store.get_provider_mapping_by_provider_id(workspace_id, "google_drive", file_id)
        meta = change.get("file") or {}

        if removed:
            if not mapping:
                return "skipped"
            item_id = str(mapping["item_id"])
            item = self.store.get_item(workspace_id, item_id, include_trashed=True)
            if item and not item.get("trashed_at"):
                self.store.trash(workspace_id, item_id, actor_id=actor_id)
            self.store.upsert_provider_mapping(
                workspace_id,
                item_id,
                provider="google_drive",
                provider_item_id=file_id,
                provider_revision=str(meta.get("version") or mapping.get("provider_revision") or ""),
                content_authority="google",
                conflict_state=None,
                metadata={"tombstone": True},
            )
            return "applied"

        name = sanitize_name(str(meta.get("name") or "Untitled"))
        mime = str(meta.get("mimeType") or "application/octet-stream")
        kind = vault_kind_for_google_mime(mime)
        remote_rev = str(meta.get("version") or meta.get("headRevisionId") or "")

        if mapping:
            item_id = str(mapping["item_id"])
            item = self.store.get_item(workspace_id, item_id, include_trashed=True)
            if not item:
                return "skipped"
            local_authority = item.get("content_authority") or "workspace"
            local_dirty = bool((item.get("metadata") or {}).get("local_dirty"))
            mapped_rev = str(mapping.get("provider_revision") or "")
            if local_authority == "workspace" and local_dirty and mapped_rev and mapped_rev != remote_rev:
                # Preserve both versions: keep local, create conflict sibling from remote.
                conflict = self.service.create_text_item(
                    workspace_id,
                    f"{name} (Google conflict)",
                    content=str(meta.get("description") or f"Remote revision {remote_rev}"),
                    kind="markdown" if kind != "folder" else "markdown",
                    parent_id=item.get("parent_id"),
                    actor_id=actor_id,
                )
                self.store.update_item(
                    workspace_id,
                    conflict["id"],
                    content_authority="google",
                    actor_id=actor_id,
                    bump_revision=False,
                )
                self.store.upsert_provider_mapping(
                    workspace_id,
                    item_id,
                    provider="google_drive",
                    provider_item_id=file_id,
                    provider_revision=mapped_rev,
                    content_authority="workspace",
                    conflict_state="both_preserved",
                    metadata={"remote_revision": remote_rev, "conflict_item_id": conflict["id"]},
                )
                self.store.upsert_provider_mapping(
                    workspace_id,
                    conflict["id"],
                    provider="google_drive",
                    provider_item_id=f"{file_id}:conflict:{remote_rev}",
                    provider_revision=remote_rev,
                    content_authority="google",
                    conflict_state="both_preserved",
                    metadata={"source_item_id": item_id},
                )
                return "conflict"

            # Safe apply remote metadata rename.
            if item.get("name") != name:
                self.store.update_item(workspace_id, item_id, name=name, actor_id=actor_id, bump_revision=False)
            self.store.upsert_provider_mapping(
                workspace_id,
                item_id,
                provider="google_drive",
                provider_item_id=file_id,
                provider_revision=remote_rev,
                content_authority="google",
                conflict_state=None,
                metadata={"mimeType": mime},
            )
            return "applied"

        # New remote file -> create vault item under root mapping folder if any.
        conn = self.store.get_drive_connection(workspace_id) or {}
        parent_id = conn.get("vault_root_item_id")
        if kind == "folder":
            created = self.service.create_folder(workspace_id, name, parent_id=parent_id, actor_id=actor_id)
        else:
            created = self.service.create_text_item(
                workspace_id,
                name,
                content="",
                kind=kind if kind != "binary_upload" else "plain_text",
                parent_id=parent_id,
                actor_id=actor_id,
            )
        self.store.update_item(
            workspace_id,
            created["id"],
            content_authority="google",
            actor_id=actor_id,
            bump_revision=False,
        )
        self.store.upsert_provider_mapping(
            workspace_id,
            created["id"],
            provider="google_drive",
            provider_item_id=file_id,
            provider_revision=remote_rev,
            content_authority="google",
            conflict_state=None,
            metadata={"mimeType": mime},
        )
        return "applied"

    def push_item(
        self,
        workspace_id: str,
        item_id: str,
        *,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        conn = self.store.get_drive_connection(workspace_id)
        if not conn or not conn.get("connected"):
            raise VaultError("not_configured", "Google Drive not connected")
        mode = str(conn.get("mode") or "two_way")
        if mode == "inbound_only":
            raise VaultError("forbidden", "outbound push disabled for inbound_only mode")

        item = self.store.get_item(workspace_id, item_id, include_trashed=True)
        if not item:
            raise VaultError("not_found")
        mapping = self.store.get_provider_mapping_for_item(workspace_id, item_id, "google_drive")
        root = conn.get("root_folder_id")
        parents = [str(root)] if root else None

        if item.get("trashed_at") and mapping:
            remote = self.client.update_file(str(mapping["provider_item_id"]), trashed=True)
            self.store.upsert_provider_mapping(
                workspace_id,
                item_id,
                provider="google_drive",
                provider_item_id=str(mapping["provider_item_id"]),
                provider_revision=str(remote.get("version") or ""),
                content_authority="workspace",
                conflict_state=None,
                metadata={"trashed": True},
            )
            return {"ok": True, "action": "trash", "provider_item_id": mapping["provider_item_id"]}

        from keprix.document_vault.google.export_mime import google_create_mime_for_kind

        mime = google_create_mime_for_kind(str(item.get("kind") or "binary_upload"))
        content = b""
        try:
            if item.get("kind") != "folder":
                content = self.service.read_bytes(workspace_id, item_id)
        except VaultError:
            content = b""

        if mapping:
            remote = self.client.update_file(
                str(mapping["provider_item_id"]),
                name=str(item.get("name")),
                content=content or None,
            )
            action = "update"
            provider_item_id = str(mapping["provider_item_id"])
        else:
            remote = self.client.create_file(
                name=str(item.get("name")),
                mime_type=mime,
                parents=parents,
                content=content or None,
            )
            action = "create"
            provider_item_id = str(remote.get("id"))

        self.store.upsert_provider_mapping(
            workspace_id,
            item_id,
            provider="google_drive",
            provider_item_id=provider_item_id,
            provider_revision=str(remote.get("version") or ""),
            content_authority="workspace",
            conflict_state=None,
            metadata={"mimeType": mime},
        )
        # Clear local dirty bit after successful push.
        meta = dict(item.get("metadata") or {})
        meta.pop("local_dirty", None)
        self.store.update_item(workspace_id, item_id, metadata=meta, actor_id=actor_id, bump_revision=False)
        return {"ok": True, "action": action, "provider_item_id": provider_item_id, "remote": remote}


__all__ = ["DriveReconciler", "ReconcileResult", "ReconcileSource"]
