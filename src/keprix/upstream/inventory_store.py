"""Runtime inventory path helpers for Hermes upstream tracking."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml

PACKAGE_ROOT = Path(__file__).resolve().parent
BUNDLED_INVENTORY_PATH = PACKAGE_ROOT / "hermes_inventory.yaml"
RUNTIME_UPSTREAM_DIR = Path.home() / ".keprix" / "upstream"
RUNTIME_INVENTORY_PATH = RUNTIME_UPSTREAM_DIR / "hermes_inventory.yaml"
RUNTIME_WORK_PACKAGES_DIR = RUNTIME_UPSTREAM_DIR / "work-packages"


def runtime_upstream_dir() -> Path:
    RUNTIME_UPSTREAM_DIR.mkdir(parents=True, exist_ok=True)
    return RUNTIME_UPSTREAM_DIR


def runtime_work_packages_dir() -> Path:
    path = RUNTIME_WORK_PACKAGES_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_runtime_inventory(*, force_refresh_features: bool = False) -> Path:
    """Ensure ``~/.keprix/upstream/hermes_inventory.yaml`` exists and is writable.

    Seeds from the bundled package inventory on first run. Optionally refreshes
    ``keprix_features`` from the capability registry without wiping tracked state.
    """
    runtime_upstream_dir()
    if not RUNTIME_INVENTORY_PATH.exists():
        if BUNDLED_INVENTORY_PATH.exists():
            shutil.copy2(BUNDLED_INVENTORY_PATH, RUNTIME_INVENTORY_PATH)
        else:
            RUNTIME_INVENTORY_PATH.write_text(
                yaml.safe_dump(
                    {
                        "processed_versions": [],
                        "keprix_features": {},
                        "tracked_features": {},
                        "last_check": None,
                        "next_prompt_number": 290,
                    },
                    default_flow_style=False,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

    if force_refresh_features or _needs_feature_refresh(RUNTIME_INVENTORY_PATH):
        refresh_keprix_features(RUNTIME_INVENTORY_PATH)
    return RUNTIME_INVENTORY_PATH


def _needs_feature_refresh(path: Path) -> bool:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return True
    features = payload.get("keprix_features") or {}
    return len(features) < 15


def refresh_keprix_features(inventory_path: Path) -> dict[str, str]:
    """Merge capability registry into inventory ``keprix_features``."""
    from keprix.upstream.capability_registry import load_capability_map

    caps = load_capability_map()
    payload: dict[str, Any] = {}
    if inventory_path.exists():
        payload = yaml.safe_load(inventory_path.read_text(encoding="utf-8")) or {}
    existing = dict(payload.get("keprix_features") or {})
    existing.update(caps)
    payload["keprix_features"] = existing
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(
        yaml.safe_dump(payload, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return existing


def default_inventory_path() -> Path:
    """Prefer the runtime inventory under ``~/.keprix/upstream/``."""
    return ensure_runtime_inventory()
