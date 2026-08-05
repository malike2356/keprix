"""Shared service for conversational channel configuration (API + agent tool)."""

from __future__ import annotations

from typing import Any

from keprix.channels.channel_config_store import (
    get_configuration,
    list_configurations,
    remove_configuration,
    save_configuration,
)
from keprix.channels.channel_probes import test_channel
from keprix.channels.channel_requirements import (
    find_channel_by_alias,
    get_channel,
    get_optional_fields,
    get_required_fields,
    list_channel_summaries,
)
from keprix.channels.channel_setup_session import clear_session, collect_field


def resolve_channel_id(channel_id: str | None) -> str | None:
    if not channel_id:
        return None
    req = get_channel(channel_id) or find_channel_by_alias(channel_id)
    return req.id if req else None


def list_channels_payload() -> dict[str, Any]:
    return {
        "channels": list_configurations(include_secrets=False),
        "catalog": list_channel_summaries(),
    }


def requirements_payload(channel_id: str) -> dict[str, Any]:
    req = get_channel(channel_id) or find_channel_by_alias(channel_id)
    if req is None:
        return {"ok": False, "error": f"Unknown channel: {channel_id}"}
    required = get_required_fields(req.id)
    return {
        "ok": True,
        "id": req.id,
        "name": req.name,
        "description": req.description,
        "setup_docs": req.setup_docs,
        "requires_restart": req.requires_restart,
        "required_fields": [
            {
                "key": f.key,
                "label": f.label,
                "description": f.description,
                "sensitive": f.sensitive,
                "optional": f.optional,
                "example": f.example,
            }
            for f in required
        ],
        "optional_fields": [
            {
                "key": f.key,
                "label": f.label,
                "description": f.description,
                "sensitive": f.sensitive,
                "optional": f.optional,
                "example": f.example,
            }
            for f in get_optional_fields(req.id)
        ],
        "next_field": (
            {
                "key": required[0].key,
                "label": required[0].label,
                "description": required[0].description,
                "sensitive": required[0].sensitive,
            }
            if required
            else None
        ),
        "hint": (
            "Prefer action=collect for one-field-at-a-time setup. "
            "Pass each answered field in credentials until complete."
        ),
    }


def configure_channel(channel_id: str, credentials: dict[str, str]) -> dict[str, Any]:
    cid = resolve_channel_id(channel_id)
    if cid is None:
        return {"ok": False, "error": f"Unknown channel: {channel_id}"}
    try:
        saved = save_configuration(cid, credentials)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, **saved}


async def configure_and_test(channel_id: str, credentials: dict[str, str]) -> dict[str, Any]:
    result = configure_channel(channel_id, credentials)
    if not result.get("ok"):
        return result
    probe = await test_channel(result["id"])
    return {
        **result,
        "test": probe,
        "message": (
            f"{result.get('name')} saved. {probe.get('message')}. "
            f"{result.get('restart_hint') or ''}"
        ).strip(),
    }


async def collect_and_maybe_save(
    channel_id: str,
    credentials: dict[str, str] | None = None,
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    """BotFather flow: accumulate fields; save+test when complete."""
    progress = collect_field(channel_id, credentials=credentials, session_id=session_id)
    if not progress.get("ok"):
        return progress
    if not progress.get("complete"):
        progress.pop("credentials", None)
        return progress

    creds = progress.pop("credentials", {}) or {}
    result = await configure_and_test(progress["channel_id"], creds)
    clear_session(progress["channel_id"], session_id=session_id)
    result.pop("credentials", None)
    result["complete"] = True
    result["collected_field_keys"] = progress.get("collected_field_keys")
    return result


async def test_channel_payload(channel_id: str) -> dict[str, Any]:
    cid = resolve_channel_id(channel_id)
    if cid is None:
        return {"success": False, "message": f"Unknown channel: {channel_id}"}
    return await test_channel(cid)


def remove_channel_payload(channel_id: str) -> dict[str, Any]:
    cid = resolve_channel_id(channel_id)
    if cid is None:
        return {"ok": False, "error": f"Unknown channel: {channel_id}"}
    try:
        return remove_configuration(cid)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


def status_for_overview() -> list[dict[str, Any]]:
    """Dashboard-friendly rows (no secrets)."""
    rows = []
    for item in list_configurations(include_secrets=False):
        status = "connected" if item.get("configured") and item.get("status") != "error" else "not_configured"
        if item.get("status") == "error":
            status = "error"
        rows.append(
            {
                "id": item["id"],
                "name": item["name"],
                "status": status,
                "configured": item.get("configured"),
                "requires_restart": item.get("requires_restart"),
                "tested_at": item.get("tested_at"),
                "last_error": item.get("last_error"),
                "bot_username": (item.get("meta") or {}).get("bot_username"),
                "message_count": (item.get("meta") or {}).get("message_count", 0),
            }
        )
    return rows


def get_channel_public(channel_id: str) -> dict[str, Any] | None:
    return get_configuration(channel_id, include_secrets=False)
