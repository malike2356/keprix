"""Scout / governance conversational config (Wave 2b)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from keprix.channels.sensitive_scrub import sensitive_field_warning


@dataclass(frozen=True)
class ScoutField:
    key: str
    label: str
    description: str
    sensitive: bool
    optional: bool = False
    example: str | None = None


SCOUT_FIELDS: tuple[ScoutField, ...] = (
    ScoutField(
        key="provider_endpoint",
        label="Scout endpoint",
        description="Labyrinth Scout / governance API base URL.",
        sensitive=False,
        example="https://console.labyrinthscout.com",
    ),
    ScoutField(
        key="api_key",
        label="Scout API key",
        description="API key from Scout (stored in the local governance vault).",
        sensitive=True,
        example="scout_... (paste; do not repeat aloud)",
    ),
)

SCOUT_ALIASES = ("scout", "labyrinth", "labyrinth scout", "governance", "pair scout")


def find_scout_alias(value: str | None) -> bool:
    if not value:
        return True
    norm = " ".join(value.strip().lower().replace("_", " ").split())
    return norm in SCOUT_ALIASES or norm in {"scout", "governance"}


def scout_requirements_payload() -> dict[str, Any]:
    required = [f for f in SCOUT_FIELDS if not f.optional]
    first = required[0]
    return {
        "ok": True,
        "id": "scout",
        "name": "Labyrinth Scout",
        "description": "Pair Keprix with Scout governance (endpoint + API key).",
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
        "next_field": {
            "key": first.key,
            "label": first.label,
            "description": first.description,
            "sensitive": first.sensitive,
            "ask": (
                sensitive_field_warning(field_label=first.label)
                if first.sensitive
                else f"Please send your {first.label}."
            ),
        },
        "hint": "Prefer action=collect. Never dump the user into nested Settings.",
    }


def get_sensitive_scout_field_keys() -> set[str]:
    return {"api_key", "scout_api_key", "scout api key", "governance_api_key"}


async def scout_status_payload() -> dict[str, Any]:
    try:
        from keprix.governance.client import get_governance_client

        status = await get_governance_client().status()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "configured": False, "error": str(exc)}
    enabled = bool(status.get("enabled") or status.get("connected") or status.get("paired"))
    safe = {k: v for k, v in status.items() if "key" not in str(k).lower() and "token" not in str(k).lower()}
    return {"ok": True, "configured": enabled, "status": safe}


async def scout_connect(credentials: dict[str, str], *, user_id: str = "admin") -> dict[str, Any]:
    endpoint = (credentials.get("provider_endpoint") or "").strip()
    api_key = (credentials.get("api_key") or "").strip()
    if not endpoint:
        return {"ok": False, "error": "Missing provider_endpoint", "next_field": {"key": "provider_endpoint"}}
    if not api_key:
        return {
            "ok": False,
            "error": "Missing api_key",
            "next_field": {
                "key": "api_key",
                "sensitive": True,
                "ask": sensitive_field_warning(field_label="Scout API key"),
            },
        }
    try:
        from keprix.governance.client import get_governance_client
        from keprix.governance.enrollment import GovernanceEnrollmentError

        config = await get_governance_client().connect(
            user_id=user_id,
            provider_endpoint=endpoint,
            api_key=api_key,
        )
    except GovernanceEnrollmentError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
    safe = {k: v for k, v in (config or {}).items() if "key" not in str(k).lower()}
    return {
        "ok": True,
        "configured": True,
        "config": safe,
        "message": "Scout paired. Monitoring preferences follow Scout policy; no dashboard scavenger hunt required.",
    }


async def scout_disconnect(*, user_id: str = "admin", accept_responsibility: bool = True) -> dict[str, Any]:
    if not accept_responsibility:
        return {
            "ok": False,
            "error": "Set accept_responsibility=true to confirm local-only operation after disconnect.",
        }
    try:
        from keprix.governance.client import get_governance_client

        config = await get_governance_client().disconnect(
            user_id=user_id,
            accept_responsibility=True,
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "configured": False, "config": config, "message": "Scout disconnected."}


# Simple in-memory collect for scout (two fields)
_SCOUT_SESSIONS: dict[str, dict[str, str]] = {}


async def scout_collect(
    credentials: dict[str, str] | None = None,
    *,
    session_id: str = "default",
    user_id: str = "admin",
) -> dict[str, Any]:
    sess = _SCOUT_SESSIONS.setdefault(session_id, {})
    for k, v in (credentials or {}).items():
        if v is not None and str(v).strip():
            sess[str(k)] = str(v).strip()

    if "provider_endpoint" not in sess:
        req = scout_requirements_payload()
        return {
            "ok": True,
            "complete": False,
            "id": "scout",
            "next_field": req["next_field"],
            "message": "Let's pair Scout. Next: Scout endpoint.",
            "collected_field_keys": sorted(sess.keys()),
        }
    if "api_key" not in sess:
        return {
            "ok": True,
            "complete": False,
            "id": "scout",
            "next_field": {
                "key": "api_key",
                "label": "Scout API key",
                "sensitive": True,
                "ask": sensitive_field_warning(field_label="Scout API key"),
            },
            "message": "Got it. Next: Scout API key.",
            "collected_field_keys": sorted(sess.keys()),
        }

    result = await scout_connect(dict(sess), user_id=user_id)
    if result.get("ok"):
        _SCOUT_SESSIONS.pop(session_id, None)
        result["complete"] = True
    return result
