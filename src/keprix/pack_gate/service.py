"""Pack gate orchestration service."""

from __future__ import annotations

from typing import Any

from keprix.auth.session import auth_manager
from keprix.hub.installer import rollback_pack
from keprix.hub.manifests import PackManifest
from keprix.hub.registry import get_pack_registry
from keprix.pack_gate.gate import (
    activate_pack,
    changelog_for_version,
    deactivate_pack,
    sign_off_url,
    validate_manifest_changelog,
)
from keprix.pack_gate.notifications import notify_pack_pending_approval
from keprix.pack_gate.store import get_pack_gate_store
from keprix.governance.audit_events import emit_audit_event


async def resolve_approver_email(approver_user_id: str | None) -> str | None:
    if not approver_user_id:
        return None
    for user in auth_manager.list_users():
        if user.get("id") == approver_user_id:
            return user.get("email")
    return None


async def after_pack_install(
    *,
    workspace_id: str,
    manifest: PackManifest,
    requested_by_user_id: str | None,
    from_version: str | None = None,
) -> dict[str, Any] | None:
    store = get_pack_gate_store()
    config = await store.get_config(workspace_id)
    if not config.get("enabled") or not config.get("approver_user_id"):
        return None

    changelog_text = changelog_for_version(manifest)

    get_pack_registry().set_enabled(manifest.name, False)
    record = await store.create_record(
        workspace_id=workspace_id,
        pack_id=manifest.name,
        to_version=manifest.version,
        from_version=from_version,
        changelog_text=changelog_text,
        requested_by_user_id=requested_by_user_id,
    )
    url = sign_off_url(manifest.name, record["id"])
    if config.get("notify_on_install", True):
        await notify_pack_pending_approval(
            workspace_id=workspace_id,
            pack_name=manifest.name,
            to_version=manifest.version,
            approver_email=config.get("approver_email"),
            gate_record_id=record["id"],
            sign_off_url=url,
        )
    return {
        "gate_required": True,
        "gate_record_id": record["id"],
        "sign_off_url": url,
        "status": "pending",
    }


async def approve_record(
    *,
    workspace_id: str,
    record_id: str,
    actor: dict,
    note: str | None,
) -> dict[str, Any]:
    store = get_pack_gate_store()
    config = await store.get_config(workspace_id)
    record = await store.get_record(workspace_id, record_id)
    if record is None:
        raise ValueError("Gate record not found")
    if record.get("status") != "pending":
        raise ValueError("Gate record is not pending")
    if not _can_sign_off(actor, config):
        raise PermissionError("Only the configured approver or a super-admin can sign off")

    updated = await store.update_record_status(
        workspace_id,
        record_id,
        status="approved",
        signed_off_by_user_id=actor.get("id"),
        sign_off_note=note,
    )
    assert updated is not None
    activate_pack(record["pack_id"])
    await emit_audit_event(
        "pack_gate_approved",
        workspace_id=workspace_id,
        actor_type="user",
        actor_id=actor.get("id"),
        subject_type="pack_gate_record",
        subject_id=record_id,
        summary=f"Pack {record['pack_id']} v{record['to_version']} approved for activation",
        detail={
            "pack_id": record["pack_id"],
            "to_version": record["to_version"],
            "signed_off_by": actor.get("id"),
        },
        severity="notice",
    )
    updated["sign_off_url"] = sign_off_url(record["pack_id"], record_id)
    return updated


async def reject_record(
    *,
    workspace_id: str,
    record_id: str,
    actor: dict,
    note: str,
) -> dict[str, Any]:
    store = get_pack_gate_store()
    config = await store.get_config(workspace_id)
    record = await store.get_record(workspace_id, record_id)
    if record is None:
        raise ValueError("Gate record not found")
    if record.get("status") != "pending":
        raise ValueError("Gate record is not pending")
    if not _can_sign_off(actor, config):
        raise PermissionError("Only the configured approver or a super-admin can sign off")

    updated = await store.update_record_status(
        workspace_id,
        record_id,
        status="rejected",
        signed_off_by_user_id=actor.get("id"),
        sign_off_note=note,
    )
    assert updated is not None
    deactivate_pack(record["pack_id"])
    await emit_audit_event(
        "pack_gate_rejected",
        workspace_id=workspace_id,
        actor_type="user",
        actor_id=actor.get("id"),
        subject_type="pack_gate_record",
        subject_id=record_id,
        summary=f"Pack {record['pack_id']} v{record['to_version']} sign-off rejected",
        detail={
            "pack_id": record["pack_id"],
            "to_version": record["to_version"],
            "signed_off_by": actor.get("id"),
            "note_length": len(note or ""),
        },
        severity="warning",
    )
    updated["sign_off_url"] = sign_off_url(record["pack_id"], record_id)
    return updated


async def rollback_pack_version(
    *,
    workspace_id: str,
    pack_id: str,
    actor: dict,
    reason: str,
) -> dict[str, Any]:
    registry = get_pack_registry()
    installed = registry.get_installed(pack_id)
    if installed is None:
        raise ValueError("Pack not installed")
    current_version = installed.version
    store = get_pack_gate_store()
    previous = await store.last_approved_version(workspace_id, pack_id, before_version=current_version)
    if not previous:
        raise ValueError("No previously approved version found")

    result = rollback_pack(pack_id, previous)
    if result.get("status") != "rolled_back":
        raise ValueError(str(result.get("message") or "Rollback failed"))

    activate_pack(pack_id)
    pending_record = await store.get_record_for_version(workspace_id, pack_id, current_version)
    log = await store.append_rollback_log(
        workspace_id=workspace_id,
        pack_id=pack_id,
        rolled_back_from_version=current_version,
        rolled_back_to_version=previous,
        reason=reason,
        initiated_by_user_id=actor.get("id"),
        gate_record_id=pending_record["id"] if pending_record else None,
    )
    await emit_audit_event(
        "compliance_finding_raised",
        workspace_id=workspace_id,
        actor_type="user",
        actor_id=actor.get("id"),
        subject_type="pack",
        subject_id=pack_id,
        summary=f"Pack {pack_id} was rolled back from {current_version} to {previous}.",
        detail={
            "pack_id": pack_id,
            "severity": "warning",
            "message": f"Pack {pack_id} was rolled back from {current_version} to {previous}.",
            "reason": reason,
        },
        severity="warning",
    )
    return {"rollback": log, "pack": result.get("pack")}


def _can_sign_off(actor: dict, config: dict[str, Any]) -> bool:
    if actor.get("role") in {"admin", "owner"}:
        return True
    approver_id = config.get("approver_user_id")
    return bool(approver_id and actor.get("id") == approver_id)


async def save_gate_config(
    workspace_id: str,
    *,
    enabled: bool,
    approver_user_id: str | None,
    notify_on_install: bool,
    require_changelog: bool,
) -> dict[str, Any]:
    if enabled and not approver_user_id:
        raise ValueError("Cannot enable pack gate without approver_user_id")
    approver_email = await resolve_approver_email(approver_user_id)
    return await get_pack_gate_store().save_config(
        workspace_id,
        {
            "enabled": enabled,
            "approver_user_id": approver_user_id,
            "approver_email": approver_email,
            "notify_on_install": notify_on_install,
            "require_changelog": require_changelog,
        },
    )


def check_changelog_or_raise(workspace_id: str, manifest: PackManifest, require: bool) -> str | None:
    return validate_manifest_changelog(manifest, require=require)
