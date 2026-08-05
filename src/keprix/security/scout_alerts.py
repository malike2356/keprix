"""Per-product Scout alert configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from keprix_cli.config import get_keprix_home
from keprix.security.scout_integration import emit_scout_signal
from keprix.security.scout_types import SignalCategory, SignalSeverity


def _alerts_path() -> Path:
    return get_keprix_home() / "scout" / "product_alerts.json"


def _load() -> dict[str, Any]:
    path = _alerts_path()
    if not path.exists():
        return {"products": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"products": {}}


def _save(data: dict[str, Any]) -> None:
    path = _alerts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class ScoutAlertConfig:
    """Per-product alert routing configuration."""

    def get_product_alerts(self, product_id: str) -> dict[str, Any]:
        return dict((_load().get("products") or {}).get(product_id) or {})

    def configure_product_alerts(self, product_id: str, config: dict[str, Any]) -> dict[str, Any]:
        data = _load()
        products = dict(data.get("products") or {})
        record = {
            "alert_channels": config.get("alert_channels") or [],
            "quiet_hours": config.get("quiet_hours") or {"start": 22, "end": 7},
            "custom_rules": config.get("custom_rules") or [],
        }
        products[product_id] = record
        data["products"] = products
        _save(data)
        emit_scout_signal(
            SignalCategory.GOVERNANCE,
            SignalSeverity.INFO,
            "alerts.configured",
            f"product:{product_id}",
            record,
        )
        return record

    def list_all(self) -> dict[str, dict[str, Any]]:
        return {pid: dict(row) for pid, row in (_load().get("products") or {}).items()}
