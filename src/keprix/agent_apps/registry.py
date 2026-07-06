"""Installed agent app registry."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from keprix.agent_apps.app_manifest import ManifestValidationError, load_manifest, validate_manifest

InstallSource = Literal["template", "upload", "path", "studio", "hub"]


def _registry_root() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "agent_apps"
    except Exception:
        root = Path.home() / ".keprix" / "agent_apps"
    root.mkdir(parents=True, exist_ok=True)
    return root


def apps_install_root(base_dir: Path | None = None) -> Path:
    if base_dir is not None:
        return base_dir / "apps"
    env_dir = os.environ.get("KEPRIX_AGENT_APPS_DIR", "").strip()
    if env_dir:
        root = Path(env_dir).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        return root
    return _apps_dir(_registry_root())


def _apps_dir(root: Path) -> Path:
    apps = root / "apps"
    apps.mkdir(parents=True, exist_ok=True)
    return apps


def _ensure_safe_dest(dest: Path, apps_root: Path) -> None:
    if not str(dest.resolve()).startswith(str(apps_root.resolve())):
        raise ManifestValidationError("Install path outside configured apps directory")


@dataclass
class InstalledApp:
    name: str
    version: str
    path: str
    installed_at: str
    source: InstallSource
    source_id: str | None = None
    entrypoint: str = ""
    display_name: str = ""
    description: str = ""
    category: str = "custom"
    runtime: str = "python"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "path": self.path,
            "installed_at": self.installed_at,
            "source": self.source,
            "source_id": self.source_id,
            "entrypoint": self.entrypoint,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "runtime": self.runtime,
        }


class AgentAppRegistry:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._root = base_dir or _registry_root()
        self._root.mkdir(parents=True, exist_ok=True)
        self._index_path = self._root / "installed.json"
        self._apps: dict[str, dict[str, Any]] = {}
        if self._index_path.exists():
            self._apps = json.loads(self._index_path.read_text(encoding="utf-8"))
            self._migrate_rows()

    def _migrate_rows(self) -> None:
        changed = False
        for name, row in self._apps.items():
            if "installed_at" not in row:
                row["installed_at"] = datetime.now(timezone.utc).isoformat()
                changed = True
            if "source" not in row:
                row["source"] = "path"
                changed = True
            if "source_id" not in row:
                row["source_id"] = None
                changed = True
            if "display_name" not in row and row.get("name"):
                row["display_name"] = row["name"]
                changed = True
        if changed:
            self._save()

    def _save(self) -> None:
        self._index_path.write_text(json.dumps(self._apps, indent=2), encoding="utf-8")

    def list_apps(self) -> list[dict[str, Any]]:
        return [self._public_row(row) for row in self._apps.values()]

    def _public_row(self, row: dict[str, Any]) -> dict[str, Any]:
        public = dict(row)
        public.pop("path", None)
        return public

    def get(self, name: str) -> dict[str, Any] | None:
        row = self._apps.get(name)
        if row is None:
            return None
        return self._public_row(row)

    def get_internal(self, name: str) -> dict[str, Any] | None:
        return self._apps.get(name)

    def app_dir(self, name: str) -> Path | None:
        row = self._apps.get(name)
        if row is None:
            return None
        return Path(row["path"])

    def _resolve_apps_root(self) -> Path:
        env_dir = os.environ.get("KEPRIX_AGENT_APPS_DIR", "").strip()
        if env_dir:
            root = Path(env_dir).expanduser()
            root.mkdir(parents=True, exist_ok=True)
            return root
        return _apps_dir(self._root)

    def install(
        self,
        source_dir: Path,
        *,
        source: InstallSource = "path",
        source_id: str | None = None,
    ) -> dict[str, Any]:
        manifest = load_manifest(source_dir)
        validate_manifest(manifest)
        apps_root = self._resolve_apps_root()
        dest = apps_root / manifest.name
        _ensure_safe_dest(dest, apps_root)
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source_dir, dest)
        row = manifest.summary_dict()
        row["path"] = str(dest)
        row["installed_at"] = datetime.now(timezone.utc).isoformat()
        row["source"] = source
        row["source_id"] = source_id
        self._apps[manifest.name] = row
        self._save()
        return self._public_row(row)

    def install_from_zip_bytes(
        self,
        zip_bytes: bytes,
        *,
        source: InstallSource = "upload",
        source_id: str | None = None,
    ) -> dict[str, Any]:
        from keprix.agent_apps.install_bundle import prepare_uploaded_bundle

        app_root, temp_root = prepare_uploaded_bundle(zip_bytes)
        try:
            return self.install(app_root, source=source, source_id=source_id)
        finally:
            temp_root.cleanup()

    def uninstall(self, name: str) -> bool:
        row = self._apps.get(name)
        if row is None:
            return False
        dest = Path(row["path"])
        apps_root = self._resolve_apps_root()
        _ensure_safe_dest(dest, apps_root)
        _pre_uninstall_hook(name)
        if dest.exists():
            shutil.rmtree(dest)
        del self._apps[name]
        self._save()
        return True

    def upgrade(
        self,
        name: str,
        source_dir: Path,
        *,
        source: InstallSource | None = None,
        source_id: str | None = None,
    ) -> dict[str, Any]:
        if name not in self._apps:
            raise ManifestValidationError(f"Agent app not installed: {name}")
        manifest = load_manifest(source_dir)
        validate_manifest(manifest)
        if manifest.name != name:
            raise ManifestValidationError(
                f"Upgrade bundle name {manifest.name!r} does not match installed app {name!r}",
            )
        apps_root = self._resolve_apps_root()
        dest = Path(self._apps[name]["path"])
        _ensure_safe_dest(dest, apps_root)
        staging = dest.parent / f".{name}.staging"
        backup = dest.parent / f".{name}.backup"
        try:
            if staging.exists():
                shutil.rmtree(staging)
            shutil.copytree(source_dir, staging)
            if backup.exists():
                shutil.rmtree(backup)
            if dest.exists():
                shutil.move(str(dest), str(backup))
            shutil.move(str(staging), str(dest))
            row = manifest.summary_dict()
            row["path"] = str(dest)
            row["installed_at"] = datetime.now(timezone.utc).isoformat()
            row["source"] = source or self._apps[name].get("source", "path")
            row["source_id"] = source_id if source_id is not None else self._apps[name].get("source_id")
            self._apps[name] = row
            self._save()
            if backup.exists():
                shutil.rmtree(backup)
            return self._public_row(row)
        except Exception:
            if not dest.exists() and backup.exists():
                shutil.move(str(backup), str(dest))
            elif dest.exists() and backup.exists():
                shutil.rmtree(dest, ignore_errors=True)
                shutil.move(str(backup), str(dest))
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            raise

    def upgrade_from_zip_bytes(
        self,
        name: str,
        zip_bytes: bytes,
        *,
        source: InstallSource | None = None,
        source_id: str | None = None,
    ) -> dict[str, Any]:
        from keprix.agent_apps.install_bundle import prepare_uploaded_bundle

        app_root, temp_root = prepare_uploaded_bundle(zip_bytes)
        try:
            return self.upgrade(name, app_root, source=source or "upload", source_id=source_id)
        finally:
            temp_root.cleanup()

    def validate_only(self, source_dir: Path) -> dict[str, Any]:
        try:
            manifest = load_manifest(source_dir)
            validate_manifest(manifest)
            return {"valid": True, "manifest": manifest.summary_dict()}
        except ManifestValidationError as exc:
            return {"valid": False, "error": str(exc)}

    def installed_count(self) -> int:
        return len(self._apps)


_registry: AgentAppRegistry | None = None


def get_agent_app_registry() -> AgentAppRegistry:
    global _registry
    if _registry is None:
        _registry = AgentAppRegistry()
    return _registry


def sample_app_dir() -> Path:
    return Path(__file__).resolve().parent / "sample" / "hello_agent"


def _pre_uninstall_hook(name: str) -> None:
    from keprix.agent_apps.automation import cleanup_app_automation

    cleanup_app_automation(name)
