"""Data subject access request (DSAR) workflow."""

from __future__ import annotations

import json
import secrets
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


class DsarStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._path = (base_dir or _privacy_dir()) / "dsar.json"
        self._requests: list[dict[str, Any]] = []
        if self._path.exists():
            self._requests = json.loads(self._path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._requests, indent=2), encoding="utf-8")

    def create(self, *, user_id: str, request_type: str = "access") -> dict[str, Any]:
        row = {
            "id": f"dsar-{secrets.token_hex(4)}",
            "user_id": user_id,
            "request_type": request_type,
            "status": "pending",
            "created_at": _utcnow(),
            "completed_at": None,
            "export_path": None,
        }
        self._requests.append(row)
        self._save()
        return row

    def get(self, request_id: str) -> dict[str, Any] | None:
        for row in self._requests:
            if row.get("id") == request_id:
                return row
        return None

    def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        return [r for r in self._requests if r.get("user_id") == user_id]

    def count_pending(self) -> int:
        return sum(1 for r in self._requests if r.get("status") == "pending")

    async def fulfill(self, request_id: str) -> dict[str, Any]:
        row = self.get(request_id)
        if row is None:
            raise KeyError(request_id)
        export_dir = _privacy_dir() / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / f"{request_id}.json"

        payload: dict[str, Any] = {
            "request_id": request_id,
            "user_id": row["user_id"],
            "exported_at": _utcnow(),
            "memories": [],
            "research_jobs": [],
            "consents": [],
        }
        try:
            from keprix.memory.episodic.store import create_episodic_store

            store = create_episodic_store()
            memories = await store.list_all(row["user_id"])
            payload["memories"] = [m.to_dict() for m in memories]
        except Exception:
            pass
        try:
            from keprix.privacy.consent import get_consent_store

            payload["consents"] = get_consent_store().list_for_user(row["user_id"])
        except Exception:
            pass
        try:
            from keprix.research.store import get_research_store

            jobs = await get_research_store().list_for_user(row["user_id"])
            payload["research_jobs"] = [j.to_dict() for j in jobs]
        except Exception:
            pass

        export_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        row["status"] = "completed"
        row["completed_at"] = _utcnow()
        row["export_path"] = str(export_path)
        self._save()
        return row


_dsar_store: DsarStore | None = None


def get_dsar_store() -> DsarStore:
    global _dsar_store
    if _dsar_store is None:
        _dsar_store = DsarStore()
    return _dsar_store
