"""Local and remote pack registry."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.hub.manifests import PackManifest


def _data_root() -> Path:
    env = os.environ.get("KEPRIX_DATA_DIR", "").strip()
    if env:
        return Path(env)
    try:
        from keprix_cli.config import get_keprix_home

        return Path(get_keprix_home())
    except Exception:
        return Path.home() / ".keprix"


def hub_home() -> Path:
    path = _data_root() / "hub"
    path.mkdir(parents=True, exist_ok=True)
    return path


def repo_packages_root() -> Path:
    return Path(__file__).resolve().parents[3] / "packages"


@dataclass
class InstalledPack:
    name: str
    version: str
    type: str
    install_path: str
    enabled: bool
    installed_at: str
    manifest: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PackRegistry:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or hub_home()
        self._installed_path = self._dir / "installed.json"
        self._audit_path = self._dir / "audit.log"
        self._installed: dict[str, InstalledPack] = {}
        if self._installed_path.exists():
            for row in json.loads(self._installed_path.read_text(encoding="utf-8")):
                pack = InstalledPack(**row)
                self._installed[pack.name] = pack

    def _save(self) -> None:
        rows = [pack.to_dict() for pack in self._installed.values()]
        self._installed_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def audit(self, event: str, *, name: str, version: str, detail: str = "") -> None:
        row = {
            "event": event,
            "name": name,
            "version": version,
            "detail": detail,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        with self._audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")

    def list_installed(self) -> list[InstalledPack]:
        return sorted(self._installed.values(), key=lambda p: p.name)

    def get_installed(self, name: str) -> InstalledPack | None:
        return self._installed.get(name)

    def record_install(
        self,
        manifest: PackManifest,
        install_path: Path,
        *,
        enabled: bool = True,
    ) -> InstalledPack:
        record = InstalledPack(
            name=manifest.name,
            version=manifest.version,
            type=manifest.type,
            install_path=str(install_path),
            enabled=enabled,
            installed_at=datetime.now(timezone.utc).isoformat(),
            manifest=manifest.to_dict(),
        )
        self._installed[manifest.name] = record
        self._save()
        self.audit("install", name=manifest.name, version=manifest.version)
        return record

    def set_enabled(self, name: str, enabled: bool) -> InstalledPack | None:
        pack = self._installed.get(name)
        if pack is None:
            return None
        pack.enabled = enabled
        self._save()
        self.audit("enable" if enabled else "disable", name=name, version=pack.version)
        return pack

    def disable(self, name: str) -> InstalledPack | None:
        pack = self._installed.get(name)
        if pack is None:
            return None
        pack.enabled = False
        self._save()
        self.audit("disable", name=name, version=pack.version)
        return pack

    def remove(self, name: str) -> InstalledPack | None:
        pack = self._installed.pop(name, None)
        if pack is None:
            return None
        self._save()
        self.audit("remove", name=name, version=pack.version)
        return pack

    def discover_catalog(self) -> list[PackManifest]:
        manifests: list[PackManifest] = []
        root = repo_packages_root()
        for category in ("packs", "templates", "connectors"):
            category_dir = root / category
            if not category_dir.exists():
                continue
            for pack_dir in sorted(category_dir.iterdir()):
                manifest_path = pack_dir / "manifest.json"
                if manifest_path.exists():
                    data = json.loads(manifest_path.read_text(encoding="utf-8"))
                    manifests.append(PackManifest.from_dict(data))
        remote_index = self._dir / "remote-index.json"
        if remote_index.exists():
            for row in json.loads(remote_index.read_text(encoding="utf-8")):
                manifests.append(PackManifest.from_dict(row))
        return manifests

    def find_catalog_pack(self, name: str, version: str | None = None) -> tuple[Path, PackManifest] | None:
        root = repo_packages_root()
        for category in ("packs", "templates", "connectors"):
            pack_dir = root / category / name
            manifest_path = pack_dir / "manifest.json"
            if not manifest_path.exists():
                continue
            manifest = PackManifest.from_dict(json.loads(manifest_path.read_text(encoding="utf-8")))
            if version and manifest.version != version:
                continue
            return pack_dir, manifest
        return None


_registry: PackRegistry | None = None


def get_pack_registry() -> PackRegistry:
    global _registry
    if _registry is None:
        _registry = PackRegistry()
    return _registry
