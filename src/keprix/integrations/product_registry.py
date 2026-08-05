"""Scout product registration for multi-product Keprix deployments."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from keprix_cli.config import get_keprix_home


def _registry_path() -> Path:
    return get_keprix_home() / "products" / "scout_registry.yaml"


def _load_registry() -> dict[str, Any]:
    path = _registry_path()
    if not path.exists():
        return {"products": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {"products": {}}


def _save_registry(data: dict[str, Any]) -> None:
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, default_flow_style=False, sort_keys=False), encoding="utf-8")


def register_product(
    product_id: str,
    *,
    scout_enabled: bool = True,
    personas: list[str] | None = None,
    tools: list[str] | None = None,
    security_policy: str = "standard",
) -> dict[str, Any]:
    data = _load_registry()
    products = dict(data.get("products") or {})
    record = {
        "product_id": product_id,
        "scout_enabled": scout_enabled,
        "personas": personas or [],
        "tools": tools or [],
        "security_policy": security_policy,
    }
    products[product_id] = record
    data["products"] = products
    _save_registry(data)
    return record


def list_registered_products() -> list[dict[str, Any]]:
    data = _load_registry()
    products = data.get("products") or {}
    return [dict(row) for row in products.values()]


def get_product(product_id: str) -> dict[str, Any] | None:
    data = _load_registry()
    row = (data.get("products") or {}).get(product_id)
    return dict(row) if row else None
