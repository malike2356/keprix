"""Google Workspace sidecar bridge and mockable native interface."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from keprix.integrations.google_workspace.oauth_store import (
    DEFAULT_SCOPES,
    GoogleWorkspaceOAuthStore,
    default_credentials_path,
    default_token_path,
)


class GoogleWorkspaceError(RuntimeError):
    """User-facing connector error."""


@dataclass
class GoogleWorkspaceConfig:
    enabled: bool = False
    credentials_path: str = ""
    token_path: str = ""
    scopes: list[str] = field(default_factory=lambda: list(DEFAULT_SCOPES))
    bridge_command: str = ""
    use_gws_cli: bool = False
    service_account_mode: bool = False

    @classmethod
    def from_env(cls) -> "GoogleWorkspaceConfig":
        return cls(
            enabled=os.environ.get("KEPRIX_GWS_ENABLED", "").lower() in {"1", "true", "yes", "on"},
            credentials_path=default_credentials_path(),
            token_path=str(default_token_path()),
            scopes=[scope.strip() for scope in os.environ.get("GOOGLE_WORKSPACE_SCOPES", ",".join(DEFAULT_SCOPES)).split(",") if scope.strip()],
            bridge_command=os.environ.get("GOOGLE_WORKSPACE_BRIDGE_CMD", ""),
            use_gws_cli=os.environ.get("GOOGLE_WORKSPACE_USE_GWS_CLI", "").lower() in {"1", "true", "yes", "on"},
            service_account_mode=os.environ.get("GOOGLE_WORKSPACE_SERVICE_ACCOUNT_MODE", "").lower() in {"1", "true", "yes", "on"},
        )

    def public_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "credentials_path_set": bool(self.credentials_path),
            "token_path": self.token_path,
            "scopes": self.scopes,
            "bridge_command_set": bool(self.bridge_command),
            "use_gws_cli": self.use_gws_cli,
            "service_account_mode": self.service_account_mode,
        }


class GoogleWorkspaceBridge:
    def __init__(self, config: GoogleWorkspaceConfig | None = None, store: GoogleWorkspaceOAuthStore | None = None) -> None:
        self.config = config or GoogleWorkspaceConfig.from_env()
        self.store = store or GoogleWorkspaceOAuthStore(self.config.token_path or None)

    def status(self) -> dict[str, Any]:
        token = self.store.load()
        missing: list[str] = []
        if not self.config.credentials_path:
            missing.append("GOOGLE_WORKSPACE_CREDENTIALS_PATH")
        elif not Path(self.config.credentials_path).expanduser().is_file():
            missing.append("OAuth client JSON file")
        return {
            "connected": token.connected,
            "account_email": token.account_email,
            "scopes": token.scopes or self.config.scopes,
            "config": self.config.public_dict(),
            "missing_setup": missing,
            "setup_error": self.setup_error(missing) if missing else None,
        }

    def setup_error(self, missing: list[str] | None = None) -> str:
        missing = missing if missing is not None else self.status().get("missing_setup", [])
        if not missing:
            return ""
        return (
            "Google Workspace is not connected. Create an OAuth desktop client in Google Cloud, "
            "enable Gmail, Calendar, Drive, and Sheets APIs, then set GOOGLE_WORKSPACE_CREDENTIALS_PATH."
        )

    def auth_url(self, redirect_uri: str = "http://localhost:8751/api/integrations/google-workspace/oauth/callback") -> dict[str, Any]:
        if not self.config.credentials_path:
            raise GoogleWorkspaceError(self.setup_error(["GOOGLE_WORKSPACE_CREDENTIALS_PATH"]))
        params = urlencode(
            {
                "client_id": self._client_id(),
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": " ".join(self.config.scopes),
                "access_type": "offline",
                "prompt": "consent",
            }
        )
        return {"auth_url": f"https://accounts.google.com/o/oauth2/v2/auth?{params}", "scopes": self.config.scopes}

    def exchange_callback(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not payload.get("code") and not payload.get("access_token"):
            raise GoogleWorkspaceError("OAuth callback requires code or access_token.")
        token = self.store.save_from_callback(payload)
        return token.public_dict()

    def logout(self) -> dict[str, Any]:
        self.store.clear()
        return {"connected": False}

    def call(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        if self.config.bridge_command:
            return self._call_command(self.config.bridge_command, tool, args)
        if self.config.use_gws_cli:
            if not shutil.which("gws"):
                raise GoogleWorkspaceError("gws CLI was requested but is not on PATH.")
            return self._call_command("gws", tool, args)
        raise GoogleWorkspaceError(self.setup_error() or "Set GOOGLE_WORKSPACE_BRIDGE_CMD to a Google Workspace sidecar command.")

    def gmail_list(self, query: str = "", max_results: int = 10) -> dict[str, Any]:
        return self.call("gws_gmail_list", {"query": query, "max_results": max_results})

    def gmail_send(self, to: str, subject: str, body: str, confirm: bool = False) -> dict[str, Any]:
        if not confirm:
            return {"requires_confirmation": True, "message": "Set confirm=true before sending Gmail messages."}
        return self.call("gws_gmail_send", {"to": to, "subject": subject, "body": body, "confirm": True})

    def calendar_list(self, time_min: str | None = None, max_results: int = 10) -> dict[str, Any]:
        return self.call("gws_calendar_list", {"time_min": time_min, "max_results": max_results})

    def calendar_create(self, summary: str, start: str, end: str, attendees: list[str] | None = None, confirm: bool = False) -> dict[str, Any]:
        if not confirm:
            return {"requires_confirmation": True, "message": "Set confirm=true before creating Calendar events."}
        return self.call("gws_calendar_create", {"summary": summary, "start": start, "end": end, "attendees": attendees or [], "confirm": True})

    def drive_search(self, query: str, max_results: int = 10) -> dict[str, Any]:
        return self.call("gws_drive_search", {"query": query, "max_results": max_results})

    def sheets_read(self, spreadsheet_id: str, range_name: str) -> dict[str, Any]:
        return self.call("gws_sheets_read", {"spreadsheet_id": spreadsheet_id, "range": range_name})

    def _client_id(self) -> str:
        path = Path(self.config.credentials_path).expanduser()
        if not path.is_file():
            return ""
        data = json.loads(path.read_text(encoding="utf-8"))
        return str((data.get("installed") or data.get("web") or {}).get("client_id", ""))

    def _call_command(self, command: str, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        payload = {"tool": tool, "args": args, "token_path": self.config.token_path, "credentials_path": self.config.credentials_path}
        try:
            completed = subprocess.run(
                shlex.split(command),
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=False,
                timeout=60,
            )
        except OSError as exc:
            raise GoogleWorkspaceError(f"Google Workspace bridge unavailable: {exc}") from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "bridge command failed"
            raise GoogleWorkspaceError(f"Google Workspace bridge failed: {detail}")
        try:
            data = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise GoogleWorkspaceError("Google Workspace bridge returned invalid JSON.") from exc
        if isinstance(data, dict) and data.get("error"):
            raise GoogleWorkspaceError(str(data["error"]))
        return data if isinstance(data, dict) else {"result": data}
