"""Durable product-sidecar job and event persistence under KEPRIX_DATA_DIR."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any


def sidecar_data_dir() -> Path:
    raw = (os.environ.get("KEPRIX_DATA_DIR") or "").strip()
    if raw:
        base = Path(raw)
    else:
        base = Path.home() / ".keprix"
    path = base / "product_sidecar"
    path.mkdir(parents=True, exist_ok=True)
    return path


class DurableJsonStore:
    """Simple JSON file persistence with in-memory cache."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._lock = threading.RLock()
        self._path = sidecar_data_dir() / f"{name}.json"
        self._data: dict[str, Any] = {"items": {}, "meta": {}}
        self._load()

    def rebind(self) -> None:
        """Refresh path after KEPRIX_DATA_DIR changes (tests)."""
        with self._lock:
            self._path = sidecar_data_dir() / f"{self._name}.json"
            self._data = {"items": {}, "meta": {}}
            self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self._data = raw
                self._data.setdefault("items", {})
                self._data.setdefault("meta", {})
        except (OSError, json.JSONDecodeError):
            self._data = {"items": {}, "meta": {}}

    def _flush(self) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, sort_keys=True, default=str), encoding="utf-8")
        tmp.replace(self._path)

    def reset_for_tests(self) -> None:
        with self._lock:
            self._data = {"items": {}, "meta": {}}
            if self._path.exists():
                self._path.unlink()

    def put(self, key: str, value: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            row = dict(value)
            self._data["items"][key] = row
            self._flush()
            return dict(row)

    def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._data["items"].get(key)
            return dict(row) if row else None

    def delete(self, key: str) -> bool:
        with self._lock:
            if key not in self._data["items"]:
                return False
            del self._data["items"][key]
            self._flush()
            return True

    def items(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(v) for v in self._data["items"].values()]

    def set_meta(self, key: str, value: Any) -> None:
        with self._lock:
            self._data["meta"][key] = value
            self._flush()

    def get_meta(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data["meta"].get(key, default)


class ProvisionReceiptStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._dir = sidecar_data_dir() / "provision"
        self._dir.mkdir(parents=True, exist_ok=True)

    def reset_for_tests(self) -> None:
        with self._lock:
            for path in self._dir.glob("*.json"):
                path.unlink()

    def write(self, product_key: str, receipt: dict[str, Any]) -> Path:
        with self._lock:
            path = self._dir / f"{product_key}.json"
            # Never persist secrets
            safe = {k: v for k, v in receipt.items() if "secret" not in k.lower() and "token" not in k.lower()}
            path.write_text(json.dumps(safe, indent=2, sort_keys=True, default=str), encoding="utf-8")
            return path

    def read(self, product_key: str) -> dict[str, Any] | None:
        path = self._dir / f"{product_key}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_products(self) -> list[str]:
        return sorted(p.stem for p in self._dir.glob("*.json"))


_PROVISION = ProvisionReceiptStore()


def get_provision_store() -> ProvisionReceiptStore:
    return _PROVISION


def now_ts() -> float:
    return time.time()
