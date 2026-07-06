"""Pack update checks."""

from __future__ import annotations

from keprix.hub.manifests import PackManifest
from keprix.hub.registry import PackRegistry, get_pack_registry


def available_updates(registry: PackRegistry | None = None) -> list[dict[str, str]]:
    reg = registry or get_pack_registry()
    installed = {pack.name: pack.version for pack in reg.list_installed()}
    updates: list[dict[str, str]] = []
    for manifest in reg.discover_catalog():
        current = installed.get(manifest.name)
        if current and current != manifest.version:
            updates.append(
                {
                    "name": manifest.name,
                    "installed_version": current,
                    "available_version": manifest.version,
                }
            )
    return updates


def dependency_errors(manifest: PackManifest, registry: PackRegistry | None = None) -> list[str]:
    reg = registry or get_pack_registry()
    installed_names = {pack.name for pack in reg.list_installed()}
    missing = [dep for dep in manifest.dependencies if dep not in installed_names]
    return [f"missing dependency: {dep}" for dep in missing]
