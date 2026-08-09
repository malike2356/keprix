"""Drive API client with injectable transport (Prompt 649).

Real HTTP calls are optional; tests inject FakeDriveTransport. Missing
credentials surface as VaultError not_configured, never fake success.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from keprix.document_vault.google.grants import DriveGrant
from keprix.document_vault.models import VaultError


class DriveTransport(Protocol):
    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        data: bytes | None = None,
    ) -> dict[str, Any]: ...


@dataclass
class FakeDriveTransport:
    """In-memory Drive API stub for unit tests."""

    files: dict[str, dict[str, Any]] = field(default_factory=dict)
    changes: list[dict[str, Any]] = field(default_factory=list)
    start_page_token: str = "1"
    page_token: str = "1"
    channels: dict[str, dict[str, Any]] = field(default_factory=dict)
    rate_limited: bool = False
    revoked: bool = False
    outage: bool = False
    upload_calls: list[dict[str, Any]] = field(default_factory=list)
    _change_cursor: int = 0

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        data: bytes | None = None,
    ) -> dict[str, Any]:
        if self.outage:
            raise VaultError("provider_outage", "Google Drive unavailable")
        if self.revoked:
            raise VaultError("auth_revoked", "Google OAuth revoked")
        if self.rate_limited:
            raise VaultError("rate_limited", "Google Drive rate limit")

        params = params or {}
        method = method.upper()

        if path == "/drive/v3/changes/startPageToken" and method == "GET":
            return {"startPageToken": self.start_page_token}

        if path == "/drive/v3/changes" and method == "GET":
            page_token = str(params.get("pageToken") or self.page_token)
            page_size = int(params.get("pageSize") or 100)
            # Paginate from _change_cursor using pageToken as offset marker.
            try:
                offset = int(page_token) - 1 if page_token.isdigit() else 0
            except ValueError:
                offset = 0
            slice_end = offset + page_size
            batch = self.changes[offset:slice_end]
            next_token = None
            if slice_end < len(self.changes):
                next_token = str(slice_end + 1)
            new_start = str(len(self.changes) + 1)
            return {
                "changes": batch,
                "nextPageToken": next_token,
                "newStartPageToken": new_start if not next_token else None,
            }

        if path == "/drive/v3/files" and method == "POST":
            file_id = f"gfile_{len(self.files) + 1}"
            body = dict(json_body or {})
            body["id"] = file_id
            body.setdefault("mimeType", "text/plain")
            body.setdefault("name", "Untitled")
            body["version"] = "1"
            body["md5Checksum"] = "fake"
            self.files[file_id] = body
            self.upload_calls.append({"op": "create", "body": body, "data": data})
            return body

        if path.startswith("/drive/v3/files/") and method == "PATCH":
            file_id = path.rsplit("/", 1)[-1]
            existing = self.files.get(file_id) or {"id": file_id}
            existing.update(json_body or {})
            existing["version"] = str(int(existing.get("version") or 1) + 1)
            self.files[file_id] = existing
            self.upload_calls.append({"op": "update", "id": file_id, "body": existing, "data": data})
            return existing

        if path.startswith("/drive/v3/files/") and method == "GET":
            file_id = path.rsplit("/", 1)[-1].split("?")[0]
            if file_id not in self.files:
                raise VaultError("not_found", f"drive file {file_id}")
            return self.files[file_id]

        if path.endswith("/watch") and method == "POST":
            channel_id = (json_body or {}).get("id") or f"chan_{len(self.channels) + 1}"
            resource_id = f"res_{len(self.channels) + 1}"
            rec = {
                "id": channel_id,
                "resourceId": resource_id,
                "expiration": str(int(__import__("time").time() * 1000) + 30 * 86_400_000),
                "token": (json_body or {}).get("token"),
            }
            self.channels[channel_id] = rec
            return rec

        if path == "/drive/v3/channels/stop" and method == "POST":
            cid = (json_body or {}).get("id")
            if cid in self.channels:
                del self.channels[cid]
            return {}

        if path == "/oauth2/v4/token" and method == "POST":
            return {
                "access_token": "refreshed-access",
                "expires_in": 3600,
                "token_type": "Bearer",
            }

        raise VaultError("unsupported_kind", f"fake transport path {method} {path}")


class DriveClient:
    def __init__(self, grant: DriveGrant, transport: DriveTransport | None = None) -> None:
        if not grant.access_token and not grant.refresh_token:
            raise VaultError("not_configured", "Google Drive OAuth grant missing")
        self.grant = grant
        self.transport = transport or FakeDriveTransport()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.grant.access_token}"}

    def refresh_access_token(self, *, client_id: str = "", client_secret: str = "") -> DriveGrant:
        if not self.grant.refresh_token:
            raise VaultError("auth_revoked", "No refresh token; reconnect Google Drive")
        payload = self.transport.request(
            "POST",
            "/oauth2/v4/token",
            json_body={
                "grant_type": "refresh_token",
                "refresh_token": self.grant.refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        self.grant.access_token = str(payload.get("access_token") or self.grant.access_token)
        return self.grant

    def start_page_token(self) -> str:
        data = self.transport.request("GET", "/drive/v3/changes/startPageToken", headers=self._headers())
        return str(data.get("startPageToken") or "1")

    def list_changes(self, page_token: str, *, page_size: int = 100) -> dict[str, Any]:
        return self.transport.request(
            "GET",
            "/drive/v3/changes",
            params={
                "pageToken": page_token,
                "pageSize": page_size,
                "includeItemsFromAllDrives": "false",
                "supportsAllDrives": "false",
            },
            headers=self._headers(),
        )

    def create_file(
        self,
        *,
        name: str,
        mime_type: str,
        parents: list[str] | None = None,
        content: bytes | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name, "mimeType": mime_type}
        if parents:
            body["parents"] = parents
        return self.transport.request(
            "POST",
            "/drive/v3/files",
            json_body=body,
            headers=self._headers(),
            data=content,
        )

    def update_file(
        self,
        file_id: str,
        *,
        name: str | None = None,
        content: bytes | None = None,
        add_parents: list[str] | None = None,
        remove_parents: list[str] | None = None,
        trashed: bool | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if trashed is not None:
            body["trashed"] = trashed
        params: dict[str, Any] = {}
        if add_parents:
            params["addParents"] = ",".join(add_parents)
        if remove_parents:
            params["removeParents"] = ",".join(remove_parents)
        return self.transport.request(
            "PATCH",
            f"/drive/v3/files/{file_id}",
            params=params or None,
            json_body=body,
            headers=self._headers(),
            data=content,
        )

    def get_file(self, file_id: str) -> dict[str, Any]:
        return self.transport.request("GET", f"/drive/v3/files/{file_id}", headers=self._headers())

    def watch_changes(self, *, channel_id: str, address: str, token: str, page_token: str) -> dict[str, Any]:
        return self.transport.request(
            "POST",
            "/drive/v3/changes/watch",
            params={"pageToken": page_token},
            json_body={
                "id": channel_id,
                "type": "web_hook",
                "address": address,
                "token": token,
            },
            headers=self._headers(),
        )

    def stop_channel(self, channel_id: str, resource_id: str) -> None:
        self.transport.request(
            "POST",
            "/drive/v3/channels/stop",
            json_body={"id": channel_id, "resourceId": resource_id},
            headers=self._headers(),
        )


__all__ = ["DriveClient", "DriveTransport", "FakeDriveTransport"]
