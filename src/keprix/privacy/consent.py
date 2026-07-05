"""GDPR consent records."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _privacy_dir() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "privacy"
    except Exception:
        root = Path.home() / ".keprix" / "privacy"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConsentStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._path = (base_dir or _privacy_dir()) / "consents.json"
        self._records: list[dict[str, Any]] = []
        if self._path.exists():
            self._records = json.loads(self._path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._records, indent=2), encoding="utf-8")

    def record(
        self,
        *,
        user_id: str,
        purpose: str,
        granted: bool,
        ip_hash: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "purpose": purpose,
            "granted": granted,
            "ip_hash": ip_hash,
            "metadata": metadata or {},
            "recorded_at": _utcnow(),
        }
        self._records.append(row)
        self._save()
        return row

    def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        return [r for r in self._records if r.get("user_id") == user_id]

    def latest(self, user_id: str, purpose: str) -> dict[str, Any] | None:
        matches = [r for r in self._records if r.get("user_id") == user_id and r.get("purpose") == purpose]
        if not matches:
            return None
        return sorted(matches, key=lambda r: r.get("recorded_at", ""))[-1]


_consent_store: ConsentStore | None = None


def get_consent_store() -> ConsentStore:
    global _consent_store
    if _consent_store is None:
        _consent_store = ConsentStore()
    return _consent_store
