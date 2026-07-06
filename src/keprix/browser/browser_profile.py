"""Encrypted browser profile storage."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from keprix.security.vault_service import _decrypt_bytes, _encrypt_bytes


class ProfileKind(str, Enum):
    FRESH = "fresh"
    PERSISTENT = "persistent"
    AUTHENTICATED = "authenticated"
    READ_ONLY = "read_only"
    DISPOSABLE = "disposable"


@dataclass
class BrowserProfile:
    id: str
    workspace_id: str
    name: str
    kind: ProfileKind
    vault_credential_id: str | None = None
    read_only: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data


def _profile_root() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "browser" / "profiles"
    except Exception:
        root = Path.home() / ".keprix" / "browser" / "profiles"
    root.mkdir(parents=True, exist_ok=True)
    return root


class BrowserProfileStore:
    """Workspace-scoped browser profiles with encrypted cookie/session blobs."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._root = base_dir or _profile_root()
        self._root.mkdir(parents=True, exist_ok=True)
        self._index_path = self._root / "profiles.json"
        self._profiles: dict[str, BrowserProfile] = {}
        if self._index_path.exists():
            for row in json.loads(self._index_path.read_text(encoding="utf-8")):
                profile = BrowserProfile(
                    id=row["id"],
                    workspace_id=row["workspace_id"],
                    name=row["name"],
                    kind=ProfileKind(row["kind"]),
                    vault_credential_id=row.get("vault_credential_id"),
                    read_only=bool(row.get("read_only")),
                    created_at=row.get("created_at", ""),
                    updated_at=row.get("updated_at", ""),
                )
                self._profiles[profile.id] = profile

    def _save_index(self) -> None:
        self._index_path.write_text(
            json.dumps([profile.to_dict() for profile in self._profiles.values()], indent=2),
            encoding="utf-8",
        )

    def _state_path(self, profile_id: str) -> Path:
        return self._root / f"{profile_id}.enc"

    def list_profiles(self, workspace_id: str) -> list[BrowserProfile]:
        return [p for p in self._profiles.values() if p.workspace_id == workspace_id]

    def get(self, profile_id: str, workspace_id: str) -> BrowserProfile | None:
        profile = self._profiles.get(profile_id)
        if profile is None or profile.workspace_id != workspace_id:
            return None
        return profile

    def create(
        self,
        *,
        workspace_id: str,
        name: str,
        kind: ProfileKind,
        vault_credential_id: str | None = None,
    ) -> BrowserProfile:
        profile = BrowserProfile(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            name=name,
            kind=kind,
            vault_credential_id=vault_credential_id,
            read_only=kind == ProfileKind.READ_ONLY,
        )
        self._profiles[profile.id] = profile
        self._save_index()
        if kind != ProfileKind.READ_ONLY:
            self.save_state(profile.id, workspace_id, {"cookies": [], "sessions": []})
        return profile

    def save_state(self, profile_id: str, workspace_id: str, state: dict[str, Any]) -> None:
        profile = self.get(profile_id, workspace_id)
        if profile is None:
            raise KeyError(profile_id)
        if profile.read_only:
            raise PermissionError("Profile is read-only")
        blob = _encrypt_bytes(json.dumps(state).encode("utf-8"))
        self._state_path(profile_id).write_bytes(blob)
        profile.updated_at = datetime.now(timezone.utc).isoformat()
        self._save_index()

    def load_state(self, profile_id: str, workspace_id: str) -> dict[str, Any]:
        profile = self.get(profile_id, workspace_id)
        if profile is None:
            raise KeyError(profile_id)
        path = self._state_path(profile_id)
        if not path.exists():
            return {"cookies": [], "sessions": []}
        plaintext = _decrypt_bytes(path.read_bytes())
        return json.loads(plaintext.decode("utf-8"))


_store: BrowserProfileStore | None = None


def get_profile_store() -> BrowserProfileStore:
    global _store
    if _store is None:
        _store = BrowserProfileStore()
    return _store
