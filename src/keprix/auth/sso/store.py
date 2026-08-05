"""Linked OAuth identity store (provider + subject -> user_id)."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

from keprix.auth.config import data_dir
from keprix.auth.sso.models import SsoProfile


class SsoIdentityStore:
    def __init__(self, path: str | None = None) -> None:
        base = Path(data_dir())
        base.mkdir(parents=True, exist_ok=True)
        self.path = path or str(base / "oauth_identities.json")
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {"links": []}
        self._load()

    def _load(self) -> None:
        file_path = Path(self.path)
        if not file_path.exists():
            self._data = {"links": []}
            return
        try:
            self._data = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            self._data = {"links": []}

    def _save(self) -> None:
        file_path = Path(self.path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        os.chmod(file_path, 0o600)

    @staticmethod
    def _key(provider: str, subject: str) -> str:
        return f"{provider.strip().lower()}:{subject.strip()}"

    def get_user_id(self, provider: str, subject: str) -> str | None:
        target = self._key(provider, subject)
        with self._lock:
            for row in self._data.get("links", []):
                if self._key(str(row.get("provider", "")), str(row.get("subject", ""))) == target:
                    return str(row.get("user_id") or "") or None
        return None

    def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = [
                {
                    "provider": row.get("provider"),
                    "subject": row.get("subject"),
                    "email": row.get("email"),
                    "linked_at": row.get("linked_at"),
                }
                for row in self._data.get("links", [])
                if str(row.get("user_id") or "") == str(user_id)
            ]
        return rows

    def count_for_user(self, user_id: str) -> int:
        return len(self.list_for_user(user_id))

    def link(self, user_id: str, profile: SsoProfile) -> None:
        key = self._key(profile.provider, profile.subject)
        with self._lock:
            links = self._data.setdefault("links", [])
            for row in links:
                existing_key = self._key(str(row.get("provider", "")), str(row.get("subject", "")))
                if existing_key == key:
                    if str(row.get("user_id") or "") != str(user_id):
                        raise ValueError("Identity already linked to another account")
                    row["email"] = profile.email
                    row["linked_at"] = time.time()
                    self._save()
                    return
                if str(row.get("user_id") or "") == str(user_id) and str(row.get("provider") or "") == profile.provider:
                    raise ValueError("Provider already linked to this account")
            links.append(
                {
                    "provider": profile.provider,
                    "subject": profile.subject,
                    "user_id": str(user_id),
                    "email": profile.email,
                    "linked_at": time.time(),
                }
            )
            self._save()

    def unlink(self, user_id: str, provider: str) -> bool:
        provider_key = provider.strip().lower()
        with self._lock:
            links = self._data.get("links", [])
            kept: list[dict[str, Any]] = []
            removed = False
            for row in links:
                if str(row.get("user_id") or "") == str(user_id) and str(row.get("provider") or "").lower() == provider_key:
                    removed = True
                    continue
                kept.append(row)
            if removed:
                self._data["links"] = kept
                self._save()
            return removed


sso_store = SsoIdentityStore()
