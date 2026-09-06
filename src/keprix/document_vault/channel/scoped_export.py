"""Workspace-scoped, kind-filtered vault exports and optional cloud delivery."""

from __future__ import annotations

import io
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from keprix.document_vault.service import DocumentVaultService
from keprix.document_vault.store import DocumentVaultStore

EXPORT_KINDS = frozenset({"documents", "notes", "research", "all"})
_KIND_GROUPS = {
    "documents": {"rich_document", "pdf", "binary_upload", "presentation", "spreadsheet"},
    "notes": {"markdown", "plain_text", "html"},
    "research": {"markdown", "plain_text", "html", "pdf"},
}


class ExportDestination(Protocol):
    name: str

    def status(self) -> dict[str, Any]: ...

    def upload(self, filename: str, data: bytes) -> dict[str, Any]: ...


class DisabledDestination:
    def __init__(self, name: str, reason: str) -> None:
        self.name = name
        self.reason = reason

    def status(self) -> dict[str, Any]:
        return {"name": self.name, "enabled": False, "reason": self.reason}

    def upload(self, filename: str, data: bytes) -> dict[str, Any]:
        return {"ok": False, "destination": self.name, "status": "disabled", "reason": self.reason}


class OneDriveDestination:
    name = "onedrive"

    def __init__(self, token: str, folder: str = "Keprix exports") -> None:
        self.token, self.folder = token, folder.strip("/")

    def status(self) -> dict[str, Any]:
        return {"name": self.name, "enabled": True, "folder": self.folder}

    def upload(self, filename: str, data: bytes) -> dict[str, Any]:
        import urllib.request

        path = "/".join(part for part in (self.folder, filename) if part)
        request = urllib.request.Request(
            f"https://graph.microsoft.com/v1.0/me/drive/root:/{path}:/content",
            data=data,
            method="PUT",
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/zip"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            return {
                "ok": True,
                "destination": self.name,
                "response": response.read().decode("utf-8"),
            }


class DropboxDestination:
    name = "dropbox"

    def __init__(self, token: str, folder: str = "/Keprix exports") -> None:
        self.token, self.folder = token, "/" + folder.strip("/")

    def status(self) -> dict[str, Any]:
        return {"name": self.name, "enabled": True, "folder": self.folder}

    def upload(self, filename: str, data: bytes) -> dict[str, Any]:
        import json
        import urllib.request

        request = urllib.request.Request(
            "https://content.dropboxapi.com/2/files/upload",
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/octet-stream",
                "Dropbox-API-Arg": json.dumps(
                    {"path": f"{self.folder}/{filename}", "mode": "add", "autorename": True}
                ),
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            return {
                "ok": True,
                "destination": self.name,
                "response": json.loads(response.read() or b"{}"),
            }


def destinations_from_env() -> dict[str, ExportDestination]:
    onedrive = os.environ.get("KEPRIX_ONEDRIVE_ACCESS_TOKEN", "").strip()
    dropbox = os.environ.get("KEPRIX_DROPBOX_ACCESS_TOKEN", "").strip()
    return {
        "onedrive": OneDriveDestination(onedrive)
        if onedrive
        else DisabledDestination("onedrive", "KEPRIX_ONEDRIVE_ACCESS_TOKEN is not configured"),
        "dropbox": DropboxDestination(dropbox)
        if dropbox
        else DisabledDestination("dropbox", "KEPRIX_DROPBOX_ACCESS_TOKEN is not configured"),
    }


def _matches(item: dict[str, Any], kinds: str) -> bool:
    return kinds == "all" or item.get("kind") in _KIND_GROUPS.get(kinds, set())


def build_scoped_zip(
    workspace_id: str,
    kinds: str = "all",
    *,
    store: DocumentVaultStore | None = None,
    service: DocumentVaultService | None = None,
) -> tuple[str, bytes, int]:
    if kinds not in EXPORT_KINDS:
        raise ValueError(f"kinds must be one of: {', '.join(sorted(EXPORT_KINDS))}")
    vault = service or DocumentVaultService(store=store)
    db = store or vault.store
    with db._lock:
        rows = db._fetchall(
            "SELECT * FROM document_vault_items WHERE workspace_id = ? AND trashed_at IS NULL ORDER BY id",
            (workspace_id,),
        )
    items = [db._present_item(row) for row in rows]
    selected = [
        item for item in items if item and item.get("kind") != "folder" and _matches(item, kinds)
    ]
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "manifest.json",
            json.dumps(
                {
                    "schema_version": "1.0",
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "workspace_id": workspace_id,
                    "kinds": kinds,
                    "tables": ["document_vault_items"],
                    "item_count": len(selected),
                },
                indent=2,
            ),
        )
        for item in selected:
            try:
                content = vault.read_text(workspace_id, item["id"])
            except Exception:
                content = ""
            archive.writestr(f"{item['kind']}/{item['id']}-{Path(item['name']).name}", content)
    return f"keprix-{workspace_id}-{kinds}.zip", payload.getvalue(), len(selected)


def export_scoped(
    workspace_id: str,
    kinds: str = "all",
    destination: str = "local",
    **kwargs: Any,
) -> dict[str, Any]:
    filename, data, count = build_scoped_zip(workspace_id, kinds, **kwargs)
    if destination == "local":
        return {
            "ok": True,
            "status": "ready",
            "destination": "local",
            "filename": filename,
            "bytes": data,
            "item_count": count,
        }
    target = destinations_from_env().get(destination)
    if target is None:
        return {"ok": False, "status": "unsupported_destination", "destination": destination}
    result = target.upload(filename, data)
    return {**result, "filename": filename, "item_count": count}


def destination_status() -> dict[str, dict[str, Any]]:
    return {
        "local": {"name": "local", "enabled": True},
        **{name: value.status() for name, value in destinations_from_env().items()},
    }
