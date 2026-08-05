"""Filesystem registry for installed built apps."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keprix.auth.config import data_dir
from keprix.built_apps.manifest import BuiltAppManifest, load_built_app_manifest


def built_apps_dir() -> Path:
    return Path(data_dir()) / "built_apps"


def _manifest_path(app_id: str) -> Path:
    return built_apps_dir() / app_id / "built_app.yaml"


def manifest_to_summary(manifest: BuiltAppManifest) -> dict[str, Any]:
    return {
        "id": manifest.id,
        "label": manifest.label,
        "description": manifest.description,
        "entry": manifest.entry,
        "icon": manifest.icon or "apps",
        "version": manifest.version,
    }


def manifest_to_nav_item(manifest: BuiltAppManifest) -> dict[str, str]:
    return {
        "id": f"built-app-{manifest.id}",
        "label": manifest.label,
        "href": manifest.entry,
        "icon": manifest.icon or "apps",
        "group": "installed_apps",
    }


def list_installed_apps() -> list[BuiltAppManifest]:
    root = built_apps_dir()
    if not root.exists():
        return []

    apps: list[BuiltAppManifest] = []
    for manifest_path in sorted(root.glob("*/built_app.yaml")):
        try:
            apps.append(load_built_app_manifest(manifest_path))
        except Exception:
            continue
    return apps


def get_installed_app(app_id: str) -> BuiltAppManifest | None:
    path = _manifest_path(app_id)
    if not path.is_file():
        return None
    return load_built_app_manifest(path)


def list_installed_apps_summary() -> list[dict[str, Any]]:
    return [manifest_to_summary(app) for app in list_installed_apps()]


def list_installed_apps_nav_items() -> list[dict[str, str]]:
    return [manifest_to_nav_item(app) for app in list_installed_apps()]
