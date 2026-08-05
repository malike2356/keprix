"""Shared runtime context for upgrade CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import os

from .changelog import load_changelog, release_versions
from .manifest import ProductManifest, default_ce_manifest, find_product_root, load_product_manifest
from .versions import latest_version, sort_versions


def _changelog_path() -> Path:
    from importlib.resources import files

    return Path(str(files("keprix.upgrade") / "CHANGELOG.yaml"))


def installed_keprix_version() -> str:
    """Return the installed Keprix package version."""
    try:
        from keprix_cli import __version__

        return __version__
    except Exception:
        try:
            from importlib import metadata

            return metadata.version("keprix")
        except metadata.PackageNotFoundError:
            return "0.0.0"


@dataclass
class UpgradeContext:
    """Resolved paths and versions for one upgrade invocation."""
    product_path: Path
    manifest: ProductManifest
    installed_version: str
    available_versions: list[str]
    changelog_path: Path

    @classmethod
    def resolve(cls, product_path: Path | None = None, *, allow_default: bool = False) -> "UpgradeContext":
        if product_path is not None:
            root = product_path.expanduser().resolve()
        else:
            env_path = os.environ.get("KEPRIX_UPGRADE_PRODUCT_PATH", "").strip()
            if env_path:
                root = Path(env_path).expanduser().resolve()
            else:
                home = os.environ.get("KEPRIX_HOME", "").strip()
                if home:
                    candidate = Path(home).expanduser().resolve()
                    if (candidate / "keprix.yaml").exists():
                        root = candidate
                    else:
                        root = candidate
                else:
                    root = None
                if root is None:
                    try:
                        root = find_product_root()
                    except FileNotFoundError:
                        if not allow_default:
                            raise
                        root = Path(home or Path.cwd()).expanduser().resolve()

        manifest_path = root / "keprix.yaml"
        manifest = (
            load_product_manifest(manifest_path)
            if manifest_path.exists()
            else default_ce_manifest(root)
        )
        changelog_path = _changelog_path()
        releases = load_changelog(changelog_path)
        versions = release_versions(releases)
        installed = installed_keprix_version()
        if installed not in versions:
            versions = sort_versions([*versions, installed])
        return cls(
            product_path=root,
            manifest=manifest,
            installed_version=installed,
            available_versions=versions,
            changelog_path=changelog_path,
        )

    def resolve_target(self, target: str | None) -> str:
        if not target or target == "latest":
            latest = latest_version(self.available_versions)
            if latest is None:
                raise ValueError("No target Keprix versions available.")
            return latest
        return target
