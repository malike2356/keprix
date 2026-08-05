"""Pack install and removal."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from keprix.hub.manifests import PackManifest, validate_manifest
from keprix.hub.registry import InstalledPack, get_pack_registry, hub_home
from keprix.hub.rollback import restore_snapshot, save_snapshot
from keprix.hub.scanner import requires_approval, scan_pack_dir
from keprix.hub.updates import dependency_errors
from keprix.hub.verifier import verify_manifest


def install_target(manifest: PackManifest) -> Path:
    return hub_home() / "installed" / manifest.type / manifest.name


def install_pack(
    pack_dir: Path,
    manifest: PackManifest,
    *,
    approved: bool = False,
    enabled: bool = True,
) -> dict[str, object]:
    errors = validate_manifest(manifest)
    if errors:
        return {"status": "error", "message": "; ".join(errors)}
    if not verify_manifest(manifest):
        return {"status": "error", "message": "manifest signature verification failed"}
    dep_errors = dependency_errors(manifest)
    if dep_errors:
        return {"status": "error", "message": "; ".join(dep_errors)}
    findings = scan_pack_dir(pack_dir, manifest.permissions)
    if findings.get("secrets"):
        return {"status": "error", "message": "secret patterns detected in pack files"}
    if requires_approval(manifest.risk_level, findings) and not approved:
        return {
            "status": "awaiting_approval",
            "message": "risky pack requires explicit approval",
            "findings": findings,
        }

    registry = get_pack_registry()
    target = install_target(manifest)
    existing = registry.get_installed(manifest.name)
    if existing:
        save_snapshot(manifest.name, existing.version, Path(existing.install_path), existing.manifest)

    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    for rel in manifest.files:
        src = pack_dir / rel
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True)
        elif src.exists():
            shutil.copy2(src, dest)

    record = registry.record_install(manifest, target, enabled=enabled)
    if manifest.name == "keprix-personal-os-starter":
        try:
            from keprix.agent_os.personal_os_pack import apply_personal_os_pack

            result = apply_personal_os_pack(target)
            return {"status": "installed", "pack": record.to_dict(), "post_install": result}
        except Exception as exc:
            return {"status": "error", "message": f"post-install failed: {exc}"}
    return {"status": "installed", "pack": record.to_dict()}


def uninstall_pack(name: str) -> dict[str, object]:
    registry = get_pack_registry()
    record = registry.get_installed(name)
    if record is None:
        return {"status": "error", "message": "pack not installed"}
    save_snapshot(name, record.version, Path(record.install_path), record.manifest)
    path = Path(record.install_path)
    if path.exists():
        shutil.rmtree(path)
    registry.remove(name)
    return {"status": "removed", "name": name}


def rollback_pack(name: str, version: str | None = None) -> dict[str, object]:
    registry = get_pack_registry()
    record = registry.get_installed(name)
    if record is None:
        return {"status": "error", "message": "pack not installed"}
    target = Path(record.install_path)
    snapshot = restore_snapshot(name, version, target)
    manifest = PackManifest.from_dict(json.loads((snapshot / "manifest.json").read_text(encoding="utf-8")))
    updated = registry.record_install(manifest, target)
    return {"status": "rolled_back", "pack": updated.to_dict(), "snapshot": snapshot.name}
