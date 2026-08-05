"""Promo code redemption against existing catalog prices (no new Stripe Prices)."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _catalog_path() -> Path:
    try:
        from keprix.auth.config import data_dir

        root = Path(data_dir()) / "billing"
    except Exception:
        root = Path.home() / ".keprix" / "billing"
    root.mkdir(parents=True, exist_ok=True)
    return root / "promo_codes.json"


class PromoStore:
    """Fake-catalog friendly promo map: code -> {percent_off | trial_days | price_id}."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _catalog_path()
        self._lock = threading.RLock()
        self._codes: dict[str, dict[str, Any]] = {}
        if self._path.exists():
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            self._codes = {str(k).upper(): v for k, v in (payload.get("codes") or {}).items()}

    def _save(self) -> None:
        self._path.write_text(json.dumps({"codes": self._codes}, indent=2), encoding="utf-8")

    def upsert(self, code: str, *, percent_off: int = 0, trial_days: int = 0, price_id: str | None = None) -> dict[str, Any]:
        row = {
            "code": code.upper().strip(),
            "percent_off": int(percent_off),
            "trial_days": int(trial_days),
            "price_id": price_id,
            "updated_at": _utcnow(),
        }
        with self._lock:
            self._codes[row["code"]] = row
            self._save()
        return dict(row)

    def redeem(self, code: str, *, catalog_price_id: str | None = None) -> dict[str, Any]:
        key = code.upper().strip()
        row = self._codes.get(key)
        if row is None:
            return {"ok": False, "error": "invalid_promo"}
        if row.get("price_id") and catalog_price_id and row["price_id"] != catalog_price_id:
            return {"ok": False, "error": "promo_price_mismatch"}
        return {
            "ok": True,
            "promo": dict(row),
            "applied_price_id": catalog_price_id or row.get("price_id"),
            "trial_days": int(row.get("trial_days") or 0),
            "percent_off": int(row.get("percent_off") or 0),
        }


_promo: PromoStore | None = None


def get_promo_store(path: Path | None = None) -> PromoStore:
    global _promo
    if path is not None:
        return PromoStore(path=path)
    if _promo is None:
        _promo = PromoStore()
    return _promo
