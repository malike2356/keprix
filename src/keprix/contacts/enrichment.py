"""Local contact enrichments (tags, messaging channels) that survive sync resync."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from keprix.auth.config import data_dir

_lock = threading.RLock()


def _path(user_id: str) -> Path:
    root = Path(data_dir()) / "contacts_enrichment"
    root.mkdir(parents=True, exist_ok=True)
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in (user_id or "local"))
    return root / f"{safe}.json"


def _load(user_id: str) -> dict[str, Any]:
    path = _path(user_id)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(user_id: str, data: dict[str, Any]) -> None:
    path = _path(user_id)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_enrichment(user_id: str, contact_id: str) -> dict[str, Any]:
    with _lock:
        row = _load(user_id).get(contact_id) or {}
    tags = row.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    return {
        "tags": list(tags),
        "whatsapp": row.get("whatsapp"),
        "telegram": row.get("telegram"),
        "role": row.get("role"),
    }


def set_enrichment(user_id: str, contact_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        data = _load(user_id)
        current = dict(data.get(contact_id) or {})
        if "tags" in patch:
            tags = patch.get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            current["tags"] = [str(t).strip() for t in tags if str(t).strip()]
        for key in ("whatsapp", "telegram", "role"):
            if key in patch:
                val = patch.get(key)
                current[key] = (str(val).strip() or None) if val is not None else None
        data[contact_id] = current
        _save(user_id, data)
    return get_enrichment(user_id, contact_id)


def merge_enrichment(user_id: str, contact: dict[str, Any]) -> dict[str, Any]:
    enrichment = get_enrichment(user_id, str(contact.get("id") or ""))
    out = dict(contact)
    out["tags"] = enrichment.get("tags") or []
    out["whatsapp"] = enrichment.get("whatsapp")
    out["telegram"] = enrichment.get("telegram")
    if enrichment.get("role"):
        out["role"] = enrichment["role"]
    elif contact.get("job_title") or contact.get("organisation"):
        parts = [p for p in [contact.get("job_title"), contact.get("organisation")] if p]
        out["role"] = " · ".join(parts) if parts else None
    else:
        out["role"] = None
    return out
