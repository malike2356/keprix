"""Version lock file: records installed Keprix version and enabled features per product."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

DEFAULT_LOCK_PATH = Path(".keprix-lock.yaml")


@dataclass
class LockFileBackup:
    path: str
    version: str
    created_at: str


@dataclass
class ProductLockFile:
    """Parsed .keprix-lock.yaml for a product."""
    product: str
    product_version: str
    keprix_version: str
    installed_at: str = ""
    last_upgrade_at: str = ""
    last_upgrade_from: str = ""
    features: dict[str, dict[str, Any]] = field(default_factory=dict)
    backups: list[LockFileBackup] = field(default_factory=list)
    path: Path = field(default_factory=lambda: DEFAULT_LOCK_PATH)

    def to_dict(self) -> dict[str, Any]:
        return {
            "product": self.product,
            "product_version": self.product_version,
            "keprix_version": self.keprix_version,
            "installed_at": self.installed_at,
            "last_upgrade_at": self.last_upgrade_at,
            "last_upgrade_from": self.last_upgrade_from,
            "features": self.features,
            "backups": [
                {"path": b.path, "version": b.version, "created_at": b.created_at}
                for b in self.backups
            ],
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_lockfile(lock_path: Path | None = None) -> ProductLockFile | None:
    """Load lock file if present. Returns None when missing."""
    path = (lock_path or DEFAULT_LOCK_PATH).expanduser().resolve()
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return None

    backups_raw = data.get("backups") or []
    backups: list[LockFileBackup] = []
    if isinstance(backups_raw, list):
        for item in backups_raw:
            if isinstance(item, dict):
                backups.append(
                    LockFileBackup(
                        path=str(item.get("path", "")),
                        version=str(item.get("version", "")),
                        created_at=str(item.get("created_at", "")),
                    )
                )

    features = data.get("features") or {}
    if not isinstance(features, dict):
        features = {}

    return ProductLockFile(
        product=str(data.get("product", "")),
        product_version=str(data.get("product_version", "")),
        keprix_version=str(data.get("keprix_version", "")),
        installed_at=str(data.get("installed_at", "")),
        last_upgrade_at=str(data.get("last_upgrade_at", "")),
        last_upgrade_from=str(data.get("last_upgrade_from", "")),
        features=features,
        backups=backups,
        path=path,
    )


def write_lockfile(lock: ProductLockFile, lock_path: Path | None = None) -> Path:
    """Write lock file to disk."""
    path = (lock_path or lock.path or DEFAULT_LOCK_PATH).expanduser().resolve()
    path.write_text(yaml.dump(lock.to_dict(), default_flow_style=False), encoding="utf-8")
    return path


def sync_features_from_manifest(
    lock: ProductLockFile,
    manifest_features: dict[str, Any],
    *,
    default_version: str,
) -> None:
    """Merge enabled features from keprix.yaml into the lock file."""
    for key, value in manifest_features.items():
        if not isinstance(value, dict):
            continue
        enabled = bool(value.get("enabled", False))
        entry = dict(lock.features.get(key) or {})
        entry["enabled"] = enabled
        if enabled and "version" not in entry:
            entry["version"] = default_version
        lock.features[key] = entry


def record_upgrade(
    product_path: Path,
    *,
    product: str,
    product_version: str,
    from_version: str,
    to_version: str,
    manifest_features: dict[str, Any] | None = None,
    backup_path: str | None = None,
    lock_path: Path | None = None,
) -> ProductLockFile:
    """Create or update the lock file after a successful upgrade."""
    root = product_path.expanduser().resolve()
    path = lock_path or (root / DEFAULT_LOCK_PATH)
    existing = load_lockfile(path)
    now = _now_iso()

    lock = existing or ProductLockFile(
        product=product,
        product_version=product_version,
        keprix_version=from_version,
        installed_at=now,
        path=path,
    )
    lock.product = product
    lock.product_version = product_version
    lock.keprix_version = to_version
    lock.last_upgrade_at = now
    lock.last_upgrade_from = from_version
    if not lock.installed_at:
        lock.installed_at = now

    if manifest_features:
        sync_features_from_manifest(lock, manifest_features, default_version=to_version)

    if backup_path:
        lock.backups.append(
            LockFileBackup(path=backup_path, version=from_version, created_at=now)
        )

    write_lockfile(lock, path)
    return lock
