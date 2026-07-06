"""Pack gate enforcement and activation helpers."""

from __future__ import annotations

from typing import Any

from keprix.hub.manifests import PackManifest
from keprix.hub.registry import get_pack_registry
from keprix.pack_gate.store import get_pack_gate_store


class PackGateRequired(Exception):
    def __init__(self, *, pack_id: str, version: str, workspace_id: str, gate_record_id: str) -> None:
        self.pack_id = pack_id
        self.version = version
        self.workspace_id = workspace_id
        self.gate_record_id = gate_record_id
        super().__init__(f"Pack gate sign-off required for {pack_id} {version}")


def changelog_for_version(manifest: PackManifest, version: str | None = None) -> str | None:
    target = version or manifest.version
    if not manifest.changelog:
        return None
    text = manifest.changelog.get(target)
    if text is None:
        return None
    cleaned = str(text).strip()
    return cleaned or None


def validate_manifest_changelog(manifest: PackManifest, *, require: bool) -> str | None:
    if not require:
        return changelog_for_version(manifest)
    text = changelog_for_version(manifest)
    if not text:
        raise ValueError(
            f"Pack manifest missing changelog for version {manifest.version}. "
            "This workspace requires a changelog entry for all pack updates."
        )
    return text


async def is_gate_enabled(workspace_id: str) -> bool:
    config = await get_pack_gate_store().get_config(workspace_id)
    return bool(config.get("enabled")) and bool(config.get("approver_user_id"))


async def require_activation_allowed(workspace_id: str, pack_id: str, version: str) -> None:
    if not await is_gate_enabled(workspace_id):
        return
    store = get_pack_gate_store()
    record = await store.get_record_for_version(workspace_id, pack_id, version)
    if record is None:
        registry = get_pack_registry()
        existing = registry.get_installed(pack_id)
        from_version = existing.version if existing else None
        record = await store.create_record(
            workspace_id=workspace_id,
            pack_id=pack_id,
            to_version=version,
            from_version=from_version,
            changelog_text=None,
            requested_by_user_id=None,
        )
        raise PackGateRequired(
            pack_id=pack_id,
            version=version,
            workspace_id=workspace_id,
            gate_record_id=record["id"],
        )
    if record.get("status") != "approved":
        raise PackGateRequired(
            pack_id=pack_id,
            version=version,
            workspace_id=workspace_id,
            gate_record_id=record["id"],
        )


def activate_pack(pack_id: str) -> dict[str, Any] | None:
    registry = get_pack_registry()
    pack = registry.get_installed(pack_id)
    if pack is None:
        return None
    return registry.set_enabled(pack_id, True)


def deactivate_pack(pack_id: str) -> dict[str, Any] | None:
    registry = get_pack_registry()
    pack = registry.get_installed(pack_id)
    if pack is None:
        return None
    return registry.set_enabled(pack_id, False)


def sign_off_url(pack_id: str, record_id: str) -> str:
    return f"/packs/{pack_id}/gate?record={record_id}"
