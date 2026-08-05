"""Service layer for conversational provider / BYOK configuration."""

from __future__ import annotations

from typing import Any

from keprix.api.provider_settings import (
    delete_provider_settings,
    provider_settings_snapshot,
    save_provider_settings,
    set_default_provider,
    test_provider_settings,
)
from keprix.configure.provider_requirements import (
    find_provider_by_alias,
    get_optional_fields,
    get_provider,
    get_required_fields,
    list_provider_summaries,
    validate_provider_credentials,
)
from keprix.configure.provider_setup_session import clear_provider_session, collect_provider_field


def resolve_provider_id(provider_id: str | None) -> str | None:
    if not provider_id:
        return None
    req = get_provider(provider_id) or find_provider_by_alias(provider_id)
    return req.id if req else None


def list_providers_payload() -> dict[str, Any]:
    snapshot = provider_settings_snapshot()
    rows = []
    for summary in list_provider_summaries():
        pid = str(summary["id"])
        entry = snapshot.get(pid) or {}
        rows.append(
            {
                "id": pid,
                "name": summary["name"],
                "aliases": summary["aliases"],
                "configured": bool(entry.get("connected")),
                "default_model": entry.get("default_model"),
                "is_default": bool(entry.get("is_default")),
                "status": "connected" if entry.get("connected") else "not_configured",
            }
        )
    return {"providers": rows, "catalog": list_provider_summaries()}


def requirements_payload(provider_id: str) -> dict[str, Any]:
    req = get_provider(provider_id) or find_provider_by_alias(provider_id)
    if req is None:
        return {"ok": False, "error": f"Unknown provider: {provider_id}"}
    required = get_required_fields(req.id)
    return {
        "ok": True,
        "id": req.id,
        "name": req.name,
        "description": req.description,
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
        "hint": "Prefer action=collect for one-field-at-a-time setup.",
    }


def configure_provider(provider_id: str, credentials: dict[str, str]) -> dict[str, Any]:
    pid = resolve_provider_id(provider_id)
    if pid is None:
        return {"ok": False, "error": f"Unknown provider: {provider_id}"}
    ok, message, cleaned = validate_provider_credentials(pid, credentials)
    if not ok:
        return {"ok": False, "error": message}
    req = get_provider(pid)
    assert req is not None
    try:
        if pid == "ollama":
            host = cleaned.get("host")
            if host:
                from keprix.api.provider_settings import persist_env_value

                persist_env_value("OLLAMA_HOST", host)
            if cleaned.get("default_model"):
                save_provider_settings(pid, default_model=cleaned["default_model"])
            else:
                # Touch snapshot path
                from keprix.api.chat_inference import invalidate_provider_cache

                invalidate_provider_cache()
            saved = provider_settings_snapshot().get(pid) or {}
        else:
            saved = save_provider_settings(
                pid,
                api_key=cleaned.get("api_key"),
                default_model=cleaned.get("default_model"),
            )
    except KeyError:
        return {"ok": False, "error": f"Unknown provider: {pid}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}

    probe = test_provider_settings(pid)
    return {
        "ok": True,
        "id": pid,
        "name": req.name,
        "configured": True,
        "status": saved,
        "test": probe,
        "message": (
            f"{req.name} saved. {probe.get('message')}. "
            "No dashboard trip needed; keys are in the environment for this instance."
        ).strip(),
    }


async def collect_and_maybe_save(
    provider_id: str,
    credentials: dict[str, str] | None = None,
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    progress = collect_provider_field(provider_id, credentials=credentials, session_id=session_id)
    if not progress.get("ok"):
        return progress
    if not progress.get("complete"):
        progress.pop("credentials", None)
        return progress
    creds = progress.pop("credentials", {}) or {}
    result = configure_provider(progress["provider_id"], creds)
    clear_provider_session(progress["provider_id"], session_id=session_id)
    result.pop("credentials", None)
    result["complete"] = True
    result["collected_field_keys"] = progress.get("collected_field_keys")
    return result


def test_provider_payload(provider_id: str) -> dict[str, Any]:
    pid = resolve_provider_id(provider_id)
    if pid is None:
        return {"success": False, "message": f"Unknown provider: {provider_id}"}
    probe = test_provider_settings(pid)
    return {"success": bool(probe.get("ok")), "message": probe.get("message") or ""}


def remove_provider_payload(provider_id: str) -> dict[str, Any]:
    pid = resolve_provider_id(provider_id)
    if pid is None:
        return {"ok": False, "error": f"Unknown provider: {provider_id}"}
    try:
        status = delete_provider_settings(pid)
    except KeyError:
        return {"ok": False, "error": f"Unknown provider: {pid}"}
    return {"ok": True, "id": pid, "removed": True, "status": status}


def set_default_payload(provider_id: str) -> dict[str, Any]:
    pid = resolve_provider_id(provider_id)
    if pid is None:
        return {"ok": False, "error": f"Unknown provider: {provider_id}"}
    snap = provider_settings_snapshot().get(pid) or {}
    if not snap.get("connected"):
        return {"ok": False, "error": f"{pid} is not configured yet. Collect an API key first."}
    result = set_default_provider(pid)
    return {"ok": True, **result, "message": f"Default provider set to {pid}."}
