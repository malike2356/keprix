"""Per-product Scout signal metrics."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from keprix_cli.config import get_keprix_home

_lock = threading.Lock()
_COUNTERS: dict[str, dict[str, int]] = {}


def _metrics_path() -> Path:
    return get_keprix_home() / "scout" / "product_metrics.json"


def _load() -> dict[str, Any]:
    path = _metrics_path()
    if not path.exists():
        return {"products": {}, "updated_at": None}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"products": {}, "updated_at": None}


def _save(data: dict[str, Any]) -> None:
    path = _metrics_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = time.time()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def record_signal(product_id: str, *, severity: str = "info", action: str = "") -> None:
    product_id = product_id or "keprix"
    with _lock:
        data = _load()
        products = dict(data.get("products") or {})
        row = dict(products.get(product_id) or {})
        row["signals_total"] = int(row.get("signals_total") or 0) + 1
        row["signals_24h"] = int(row.get("signals_24h") or 0) + 1
        if severity in {"critical", "emergency"}:
            row["alerts_critical"] = int(row.get("alerts_critical") or 0) + 1
        elif severity == "warning":
            row["alerts_warning"] = int(row.get("alerts_warning") or 0) + 1
        row["last_action"] = action
        row["last_signal_at"] = time.time()
        products[product_id] = row
        data["products"] = products
        _save(data)


def product_metrics(product_id: str | None = None) -> dict[str, Any]:
    data = _load()
    products = data.get("products") or {}
    if product_id:
        return dict(products.get(product_id) or {})
    return {pid: dict(row) for pid, row in products.items()}


def reset_metrics() -> None:
    with _lock:
        _save({"products": {}, "updated_at": time.time()})
