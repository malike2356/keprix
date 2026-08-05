"""JSON lead store."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path() -> Path:
    try:
        from keprix.auth.config import data_dir

        root = Path(data_dir()) / "product_leads"
    except Exception:
        root = Path.home() / ".keprix" / "product_leads"
    root.mkdir(parents=True, exist_ok=True)
    return root / "leads.json"


class LeadStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _path()
        self._lock = threading.RLock()
        self._leads: dict[str, dict[str, Any]] = {}
        if self._path.exists():
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            self._leads = {str(r["id"]): r for r in (payload.get("leads") or [])}

    def _save(self) -> None:
        self._path.write_text(
            json.dumps({"leads": list(self._leads.values())}, indent=2),
            encoding="utf-8",
        )

    def create(
        self,
        *,
        name: str,
        email: str = "",
        contact_id: str | None = None,
        campaign_id: str | None = None,
        tenant_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            from keprix.tenancy.isolation import current_tenant_id

            tid = tenant_id or current_tenant_id()
        except Exception:
            tid = tenant_id
        row = {
            "id": str(uuid.uuid4()),
            "name": name.strip(),
            "email": (email or "").strip().lower(),
            "contact_id": contact_id,
            "campaign_id": campaign_id,
            "vical_booking_id": None,
            "status": "open",
            "tenant_id": tid,
            "metadata": dict(metadata or {}),
            "created_at": _utcnow(),
            "updated_at": _utcnow(),
        }
        with self._lock:
            self._leads[row["id"]] = row
            self._save()
        return dict(row)

    def list_leads(self, *, tenant_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        rows = list(self._leads.values())
        if tenant_id:
            rows = [r for r in rows if r.get("tenant_id") in (None, tenant_id)]
        rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        return [dict(r) for r in rows[:limit]]

    def get(self, lead_id: str) -> dict[str, Any] | None:
        row = self._leads.get(lead_id)
        return dict(row) if row else None

    def link_booking(self, lead_id: str, booking_id: str) -> dict[str, Any]:
        with self._lock:
            row = self._leads.get(lead_id)
            if row is None:
                raise LookupError(lead_id)
            row["vical_booking_id"] = booking_id
            row["updated_at"] = _utcnow()
            self._save()
            return dict(row)


_store: LeadStore | None = None


def get_lead_store(path: Path | None = None) -> LeadStore:
    global _store
    if path is not None:
        return LeadStore(path=path)
    if _store is None:
        _store = LeadStore()
    return _store
