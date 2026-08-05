"""Minimal Syncthing REST client."""

from __future__ import annotations

from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json


class SyncthingError(RuntimeError):
    pass


class SyncthingClient:
    def __init__(self, base_url: str, api_key: str, timeout_s: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_s = timeout_s

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = Request(
            url,
            data=data,
            method=method,
            headers={
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw.strip() else {}
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise SyncthingError(f"Syncthing {method} {path} failed ({exc.code}): {detail or exc.reason}") from exc
        except URLError as exc:
            raise SyncthingError(f"Cannot reach Syncthing at {self.base_url}: {exc.reason}") from exc

    def system_status(self) -> dict[str, Any]:
        return self._request("GET", "/rest/system/status")

    def system_version(self) -> dict[str, Any]:
        return self._request("GET", "/rest/system/version")

    def get_config(self) -> dict[str, Any]:
        # Prefer /rest/config (newer); fall back to /rest/system/config
        try:
            return self._request("GET", "/rest/config")
        except SyncthingError:
            return self._request("GET", "/rest/system/config")

    def put_config(self, config: dict[str, Any]) -> None:
        try:
            self._request("PUT", "/rest/config", config)
            return
        except SyncthingError:
            self._request("POST", "/rest/system/config", config)

    def folder_status(self, folder_id: str) -> dict[str, Any]:
        from urllib.parse import quote

        return self._request("GET", f"/rest/db/status?folder={quote(folder_id)}")

    def completion(self, folder_id: str | None = None) -> dict[str, Any]:
        path = "/rest/db/completion"
        if folder_id:
            from urllib.parse import quote

            path += f"?folder={quote(folder_id)}"
        return self._request("GET", path)
