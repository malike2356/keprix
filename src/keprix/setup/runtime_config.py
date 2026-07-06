"""Runtime configuration with vault references."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from keprix.auth.config import data_dir
from keprix.security.vault_service import get_vault_service


class RuntimeConfigStore:
    def __init__(self, path: str | None = None) -> None:
        base = Path(data_dir())
        base.mkdir(parents=True, exist_ok=True)
        self.path = Path(path or base / "runtime_config.json")
        self._data: dict[str, Any] = {}
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}

    def save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        os.chmod(self.path, 0o600)

    def set_service(
        self,
        service_id: str,
        *,
        vault_item_id: str,
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        services = self._data.setdefault("services", {})
        services[service_id] = {
            "vault_ref": f"vault://{vault_item_id}",
            "enabled": enabled,
            "metadata": metadata or {},
        }
        self.save()

    def disable_service(self, service_id: str) -> bool:
        services = self._data.get("services", {})
        if service_id not in services:
            return False
        services[service_id]["enabled"] = False
        self.save()
        return True

    def status(self) -> dict[str, Any]:
        services = self._data.get("services", {})
        out: dict[str, Any] = {}
        for service_id, cfg in services.items():
            out[service_id] = {
                "enabled": cfg.get("enabled", False),
                "vault_ref": cfg.get("vault_ref"),
                "metadata": cfg.get("metadata", {}),
            }
        return out

    async def resolve_secret(self, service_id: str, user_id: str) -> str | None:
        cfg = self._data.get("services", {}).get(service_id)
        if not cfg or not cfg.get("enabled"):
            return None
        vault_ref = str(cfg.get("vault_ref", ""))
        if not vault_ref.startswith("vault://"):
            return None
        item_id = vault_ref.removeprefix("vault://")
        item = await get_vault_service().get_item(item_id, user_id, decrypt=True)
        return item._value if item else None


_store: RuntimeConfigStore | None = None


def get_runtime_config() -> RuntimeConfigStore:
    global _store
    if _store is None:
        _store = RuntimeConfigStore()
    return _store


def reset_runtime_config() -> None:
    global _store
    _store = RuntimeConfigStore()
