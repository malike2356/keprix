"""Local token metadata store for the Google Workspace connector."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]


def keprix_home() -> Path:
    return Path(os.environ.get("KEPRIX_HOME", Path.home() / ".keprix")).expanduser()


def default_token_path() -> Path:
    return Path(os.environ.get("GOOGLE_WORKSPACE_TOKEN_PATH", keprix_home() / "google-workspace-token.json")).expanduser()


def default_credentials_path() -> str:
    return os.environ.get("GOOGLE_WORKSPACE_CREDENTIALS_PATH", "")


@dataclass
class GoogleWorkspaceToken:
    connected: bool
    scopes: list[str] = field(default_factory=list)
    account_email: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: str | None = None
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def public_dict(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "scopes": self.scopes,
            "account_email": self.account_email,
            "expires_at": self.expires_at,
            "updated_at": self.updated_at,
        }


class GoogleWorkspaceOAuthStore:
    def __init__(self, token_path: str | Path | None = None) -> None:
        self.path = Path(token_path).expanduser() if token_path else default_token_path()

    def load(self) -> GoogleWorkspaceToken:
        if not self.path.is_file():
            return GoogleWorkspaceToken(connected=False, scopes=[])
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return GoogleWorkspaceToken(connected=False, scopes=[])
        return GoogleWorkspaceToken(
            connected=bool(data.get("connected", True)),
            scopes=[str(scope) for scope in data.get("scopes", [])],
            account_email=data.get("account_email"),
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            expires_at=data.get("expires_at"),
            updated_at=data.get("updated_at") or datetime.now(timezone.utc).isoformat(),
        )

    def save(self, token: GoogleWorkspaceToken) -> GoogleWorkspaceToken:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = token.__dict__.copy()
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        try:
            self.path.chmod(0o600)
        except OSError:
            pass
        return token

    def save_from_callback(self, payload: dict[str, Any]) -> GoogleWorkspaceToken:
        token = GoogleWorkspaceToken(
            connected=True,
            scopes=[str(scope) for scope in payload.get("scopes") or DEFAULT_SCOPES],
            account_email=payload.get("account_email"),
            access_token=payload.get("access_token") or payload.get("code"),
            refresh_token=payload.get("refresh_token"),
            expires_at=payload.get("expires_at"),
        )
        return self.save(token)

    def clear(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
