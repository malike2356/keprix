"""Workspace CRM connection credentials and feature flags (GUI-configurable).

Secrets are encrypted at rest via keprix.email.crypto and never returned in
plaintext from list/status APIs (masked last4 only). Adapters resolve workspace
credentials first, then process env fallback.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from keprix.crm.nice_schema import ensure_nice_schema
from keprix.email.crypto import decrypt_secret, encrypt_secret

CREDENTIALS_TABLE = """
CREATE TABLE IF NOT EXISTS crm_workspace_credentials (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    slot_id TEXT NOT NULL,
    label TEXT,
    value_encrypted TEXT NOT NULL,
    last4 TEXT,
    meta_json TEXT NOT NULL DEFAULT '{}',
    actor_type TEXT,
    actor_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, slot_id)
);
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class ConnectionSlot:
    slot_id: str
    group: str
    label: str
    description: str
    secret: bool = True
    env_fallbacks: tuple[str, ...] = ()
    param_key: str | None = None  # non-secret param stored in nice settings


# Catalog covers remaining Nice credential/flag gaps (454, 456, 459, 461, 464).
CONNECTION_CATALOG: tuple[ConnectionSlot, ...] = (
    # 454 CRM integrations
    ConnectionSlot(
        "hubspot_access_token",
        "crm_integrations",
        "HubSpot access token",
        "Private app token for HubSpot CRM sync.",
        env_fallbacks=("KEPRIX_HUBSPOT_ACCESS_TOKEN", "HUBSPOT_ACCESS_TOKEN"),
    ),
    ConnectionSlot(
        "salesforce_access_token",
        "crm_integrations",
        "Salesforce access token",
        "OAuth access token for Salesforce.",
        env_fallbacks=("KEPRIX_SALESFORCE_ACCESS_TOKEN", "SALESFORCE_ACCESS_TOKEN"),
    ),
    ConnectionSlot(
        "pipedrive_api_token",
        "crm_integrations",
        "Pipedrive API token",
        "Pipedrive personal API token.",
        env_fallbacks=("KEPRIX_PIPEDRIVE_API_TOKEN", "PIPEDRIVE_API_TOKEN"),
    ),
    ConnectionSlot(
        "ghl_api_key",
        "crm_integrations",
        "Go High Level API key",
        "GHL location/agency API key.",
        env_fallbacks=("KEPRIX_GHL_API_KEY", "GHL_API_KEY"),
    ),
    # 456 licensed enrichment
    ConnectionSlot(
        "clearbit_api_key",
        "enrichment",
        "Clearbit API key",
        "Licensed Clearbit (or compatible) enrichment key. Never scrapes.",
        env_fallbacks=("KEPRIX_CLEARBIT_API_KEY", "CLEARBIT_API_KEY"),
    ),
    ConnectionSlot(
        "fake_enrich_key",
        "enrichment",
        "Fake enrich key (tests)",
        "Optional key for fake_licensed provider in non-prod.",
        env_fallbacks=("KEPRIX_FAKE_ENRICH_KEY",),
    ),
    # 459 WhatsApp / SMS
    ConnectionSlot(
        "whatsapp_token",
        "messaging",
        "WhatsApp Business token",
        "Meta WhatsApp Cloud API token.",
        env_fallbacks=("KEPRIX_WHATSAPP_TOKEN", "WHATSAPP_TOKEN", "META_WHATSAPP_TOKEN"),
    ),
    ConnectionSlot(
        "whatsapp_phone_number_id",
        "messaging",
        "WhatsApp phone number id",
        "Meta phone_number_id for outbound WhatsApp.",
        secret=False,
        env_fallbacks=("KEPRIX_WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_PHONE_NUMBER_ID"),
        param_key="whatsapp_phone_number_id",
    ),
    ConnectionSlot(
        "twilio_account_sid",
        "messaging",
        "Twilio Account SID",
        "Twilio account SID for SMS.",
        secret=False,
        env_fallbacks=("KEPRIX_TWILIO_ACCOUNT_SID", "TWILIO_ACCOUNT_SID"),
        param_key="twilio_account_sid",
    ),
    ConnectionSlot(
        "twilio_auth_token",
        "messaging",
        "Twilio Auth Token",
        "Twilio auth token for SMS.",
        env_fallbacks=("KEPRIX_TWILIO_AUTH_TOKEN", "TWILIO_AUTH_TOKEN"),
    ),
    ConnectionSlot(
        "twilio_from_number",
        "messaging",
        "Twilio from number",
        "E.164 sender number for SMS.",
        secret=False,
        env_fallbacks=("KEPRIX_TWILIO_FROM_NUMBER", "TWILIO_FROM_NUMBER"),
        param_key="twilio_from_number",
    ),
    # 461 social APIs
    ConnectionSlot(
        "linkedin_client_id",
        "social",
        "LinkedIn client id",
        "LinkedIn Marketing / Lead Gen API client id.",
        secret=False,
        env_fallbacks=("LINKEDIN_CLIENT_ID", "KEPRIX_LINKEDIN_CLIENT_ID"),
        param_key="linkedin_client_id",
    ),
    ConnectionSlot(
        "linkedin_client_secret",
        "social",
        "LinkedIn client secret",
        "LinkedIn OAuth client secret.",
        env_fallbacks=("LINKEDIN_CLIENT_SECRET", "KEPRIX_LINKEDIN_CLIENT_SECRET"),
    ),
    ConnectionSlot(
        "linkedin_scopes",
        "social",
        "LinkedIn scopes",
        "Space-separated OAuth scopes granted to the app.",
        secret=False,
        env_fallbacks=("LINKEDIN_SCOPES",),
        param_key="linkedin_scopes",
    ),
    ConnectionSlot(
        "meta_app_id",
        "social",
        "Meta app id",
        "Meta Graph API app id (Lead Ads).",
        secret=False,
        env_fallbacks=("META_APP_ID", "KEPRIX_META_APP_ID"),
        param_key="meta_app_id",
    ),
    ConnectionSlot(
        "meta_app_secret",
        "social",
        "Meta app secret",
        "Meta Graph API app secret.",
        env_fallbacks=("META_APP_SECRET", "KEPRIX_META_APP_SECRET"),
    ),
    ConnectionSlot(
        "tiktok_app_id",
        "social",
        "TikTok app id",
        "TikTok Marketing API app id.",
        secret=False,
        env_fallbacks=("TIKTOK_APP_ID", "KEPRIX_TIKTOK_APP_ID"),
        param_key="tiktok_app_id",
    ),
    ConnectionSlot(
        "tiktok_app_secret",
        "social",
        "TikTok app secret",
        "TikTok Marketing API app secret.",
        env_fallbacks=("TIKTOK_APP_SECRET", "KEPRIX_TIKTOK_APP_SECRET"),
    ),
    # 464 property portals (API/feed keys when licensed)
    ConnectionSlot(
        "rightmove_feed_token",
        "property_portals",
        "Rightmove feed token",
        "Licensed Rightmove data feed token (if contracted).",
        env_fallbacks=("KEPRIX_RIGHTMOVE_FEED_TOKEN", "RIGHTMOVE_FEED_TOKEN"),
    ),
    ConnectionSlot(
        "zoopla_api_key",
        "property_portals",
        "Zoopla API key",
        "Licensed Zoopla API key (if contracted).",
        env_fallbacks=("KEPRIX_ZOOPLA_API_KEY", "ZOOPLA_API_KEY"),
    ),
)

FLAG_CATALOG: tuple[dict[str, str], ...] = (
    {
        "flag_id": "whatsapp_sms_enabled",
        "group": "messaging",
        "label": "Enable WhatsApp / SMS channels",
        "description": "Workspace Soft Wall still required before first send. Maps to KEPRIX_WHATSAPP_SMS when set in env.",
        "env": "KEPRIX_WHATSAPP_SMS",
    },
    {
        "flag_id": "linkedin_api_enabled",
        "group": "social",
        "label": "Enable LinkedIn API discovery",
        "description": "Allows linkedin_api adapter when client id/secret are set.",
        "env": "KEPRIX_LINKEDIN_API",
    },
    {
        "flag_id": "meta_graph_api_enabled",
        "group": "social",
        "label": "Enable Meta Graph discovery",
        "description": "Allows meta_graph adapter when app id/secret are set.",
        "env": "KEPRIX_META_GRAPH_API",
    },
    {
        "flag_id": "tiktok_api_enabled",
        "group": "social",
        "label": "Enable TikTok API discovery",
        "description": "Allows tiktok_api adapter when app id/secret are set.",
        "env": "KEPRIX_TIKTOK_API",
    },
    {
        "flag_id": "property_portal_adapters_enabled",
        "group": "property_portals",
        "label": "Enable property portal adapters",
        "description": "Requires legal checklist Soft Wall ack. Scrapers stay refused without licensed feed tokens.",
        "env": "KEPRIX_PROPERTY_PORTAL_ADAPTERS",
    },
    {
        "flag_id": "fake_enrich_always",
        "group": "enrichment",
        "label": "Allow fake enrich without key (dev)",
        "description": "Non-prod convenience for fake_licensed provider.",
        "env": "KEPRIX_FAKE_ENRICH_ALWAYS",
    },
)

_SLOT_BY_ID = {s.slot_id: s for s in CONNECTION_CATALOG}
_SLOT_BY_ENV: dict[str, ConnectionSlot] = {}
for _slot in CONNECTION_CATALOG:
    for _env_name in _slot.env_fallbacks:
        _SLOT_BY_ENV[_env_name] = _slot


def ensure_credentials_schema(store: Any) -> None:
    ensure_nice_schema(store)
    with store._lock:
        store._conn.executescript(CREDENTIALS_TABLE)
        store._conn.commit()


def list_catalog() -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for slot in CONNECTION_CATALOG:
        groups.setdefault(slot.group, []).append(
            {
                "slot_id": slot.slot_id,
                "label": slot.label,
                "description": slot.description,
                "secret": slot.secret,
                "env_fallbacks": list(slot.env_fallbacks),
                "param_key": slot.param_key,
            }
        )
    return {"groups": groups, "flags": list(FLAG_CATALOG)}


def _mask(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if len(raw) <= 4:
        return "****"
    return f"****{raw[-4:]}"


def _env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def get_slot_value(store: Any, workspace_id: str, slot_id: str) -> str | None:
    """Return decrypted secret/param for internal use only."""
    ensure_credentials_schema(store)
    ws = store._require_workspace(workspace_id)
    slot = _SLOT_BY_ID.get(slot_id)
    if not slot:
        return None
    row = store._fetchone(
        "SELECT * FROM crm_workspace_credentials WHERE workspace_id = ? AND slot_id = ?",
        (ws, slot_id),
    )
    if row and row.get("value_encrypted"):
        return decrypt_secret(str(row["value_encrypted"]))
    if not slot.secret and slot.param_key:
        from keprix.crm.data_quality import get_nice_settings

        settings = get_nice_settings(store, ws).get("settings") or {}
        val = settings.get(slot.param_key)
        if val:
            return str(val)
    return _env(*slot.env_fallbacks) or None


def resolve_env_names(store: Any, workspace_id: str | None, *env_names: str) -> str:
    """Resolve credential by env name list: workspace slot then process env."""
    if workspace_id:
        for name in env_names:
            slot = _SLOT_BY_ENV.get(name)
            if not slot:
                continue
            value = get_slot_value(store, workspace_id, slot.slot_id)
            if value:
                return value
    return _env(*env_names)


def resolve_any(*env_names: str, workspace_id: str | None = None, store: Any | None = None) -> str:
    if store is not None and workspace_id:
        return resolve_env_names(store, workspace_id, *env_names)
    return _env(*env_names)


def put_credential(
    store: Any,
    workspace_id: str,
    slot_id: str,
    value: str,
    *,
    actor_type: str = "user",
    actor_id: str | None = None,
    label: str | None = None,
) -> dict[str, Any]:
    ensure_credentials_schema(store)
    ws = store._require_workspace(workspace_id)
    slot = _SLOT_BY_ID.get(slot_id)
    if not slot:
        raise ValueError(f"unknown_slot:{slot_id}")
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("value_required")
    now = _utcnow()
    existing = store._fetchone(
        "SELECT * FROM crm_workspace_credentials WHERE workspace_id = ? AND slot_id = ?",
        (ws, slot_id),
    )
    rid = str(existing["id"]) if existing else str(uuid.uuid4())
    encrypted = encrypt_secret(raw)
    last4 = raw[-4:] if len(raw) >= 4 else raw
    created_at = str(existing.get("created_at") or now) if existing else now
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO crm_workspace_credentials (
                id, workspace_id, slot_id, label, value_encrypted, last4, meta_json,
                actor_type, actor_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, '{}', ?, ?, ?, ?)
            ON CONFLICT(workspace_id, slot_id) DO UPDATE SET
                label = excluded.label,
                value_encrypted = excluded.value_encrypted,
                last4 = excluded.last4,
                actor_type = excluded.actor_type,
                actor_id = excluded.actor_id,
                updated_at = excluded.updated_at
            """,
            (
                rid,
                ws,
                slot_id,
                label or slot.label,
                encrypted,
                last4,
                actor_type,
                actor_id,
                created_at,
                now,
            ),
        )
        store._conn.commit()
    # Non-secret params also mirror into nice settings for easy reads.
    if not slot.secret and slot.param_key:
        from keprix.crm.data_quality import get_nice_settings, upsert_nice_settings

        current = get_nice_settings(store, ws)
        settings = dict(current.get("settings") or {})
        settings[slot.param_key] = raw
        upsert_nice_settings(store, ws, settings=settings)
    return slot_status(store, ws, slot_id)


def delete_credential(store: Any, workspace_id: str, slot_id: str) -> dict[str, Any]:
    ensure_credentials_schema(store)
    ws = store._require_workspace(workspace_id)
    with store._lock:
        store._conn.execute(
            "DELETE FROM crm_workspace_credentials WHERE workspace_id = ? AND slot_id = ?",
            (ws, slot_id),
        )
        store._conn.commit()
    slot = _SLOT_BY_ID.get(slot_id)
    if slot and not slot.secret and slot.param_key:
        from keprix.crm.data_quality import get_nice_settings, upsert_nice_settings

        current = get_nice_settings(store, ws)
        settings = dict(current.get("settings") or {})
        settings.pop(slot.param_key, None)
        upsert_nice_settings(store, ws, settings=settings)
    return {"ok": True, "slot_id": slot_id, "deleted": True}


def slot_status(store: Any, workspace_id: str, slot_id: str) -> dict[str, Any]:
    ensure_credentials_schema(store)
    ws = store._require_workspace(workspace_id)
    slot = _SLOT_BY_ID[slot_id]
    row = store._fetchone(
        "SELECT * FROM crm_workspace_credentials WHERE workspace_id = ? AND slot_id = ?",
        (ws, slot_id),
    )
    env_present = bool(_env(*slot.env_fallbacks))
    workspace_present = bool(row and row.get("value_encrypted"))
    if not workspace_present and not slot.secret and slot.param_key:
        from keprix.crm.data_quality import get_nice_settings

        settings = get_nice_settings(store, ws).get("settings") or {}
        workspace_present = bool(settings.get(slot.param_key))
    configured = workspace_present or env_present
    return {
        "slot_id": slot.slot_id,
        "group": slot.group,
        "label": slot.label,
        "description": slot.description,
        "secret": slot.secret,
        "configured": configured,
        "source": "workspace" if workspace_present else ("env" if env_present else None),
        "masked": (f"****{row.get('last4')}" if row and row.get("last4") else ("****env" if env_present else None)),
        "env_fallbacks": list(slot.env_fallbacks),
        "updated_at": row.get("updated_at") if row else None,
    }


def connections_status(store: Any, workspace_id: str) -> dict[str, Any]:
    ensure_credentials_schema(store)
    ws = store._require_workspace(workspace_id)
    slots = [slot_status(store, ws, s.slot_id) for s in CONNECTION_CATALOG]
    flags = flag_status(store, ws)
    by_group: dict[str, list[dict[str, Any]]] = {}
    for item in slots:
        by_group.setdefault(str(item["group"]), []).append(item)
    return {
        "workspace_id": ws,
        "groups": by_group,
        "flags": flags,
        "ready_groups": {
            group: all(s["configured"] for s in items if s.get("secret") or True)
            for group, items in by_group.items()
        },
    }


def flag_status(store: Any, workspace_id: str) -> list[dict[str, Any]]:
    from keprix.crm.data_quality import get_nice_settings

    settings = get_nice_settings(store, workspace_id)
    nested = dict(settings.get("settings") or {})
    out: list[dict[str, Any]] = []
    for flag in FLAG_CATALOG:
        fid = flag["flag_id"]
        env_on = _env(flag["env"]).lower() in {"1", "true", "yes", "on"}
        # Top-level whatsapp_sms_enabled lives on nice settings row.
        if fid == "whatsapp_sms_enabled":
            ws_on = bool(settings.get("whatsapp_sms_enabled"))
        else:
            ws_on = bool(nested.get(fid))
        out.append(
            {
                **flag,
                "enabled": ws_on or env_on,
                "workspace_enabled": ws_on,
                "env_enabled": env_on,
            }
        )
    return out


def set_flag(
    store: Any,
    workspace_id: str,
    flag_id: str,
    enabled: bool,
    *,
    actor_id: str | None = None,
) -> dict[str, Any]:
    from keprix.crm.data_quality import get_nice_settings, upsert_nice_settings

    known = {f["flag_id"] for f in FLAG_CATALOG}
    if flag_id not in known:
        raise ValueError(f"unknown_flag:{flag_id}")
    ws = store._require_workspace(workspace_id)
    current = get_nice_settings(store, ws)
    if flag_id == "whatsapp_sms_enabled":
        upsert_nice_settings(store, ws, whatsapp_sms_enabled=enabled)
    else:
        nested = dict(current.get("settings") or {})
        nested[flag_id] = bool(enabled)
        if actor_id:
            nested["flags_updated_by"] = actor_id
        upsert_nice_settings(store, ws, settings=nested)
    return {"ok": True, "flags": flag_status(store, ws)}


def workspace_flag_enabled(store: Any, workspace_id: str, flag_id: str) -> bool:
    for row in flag_status(store, workspace_id):
        if row["flag_id"] == flag_id:
            return bool(row["enabled"])
    return False


def adapter_required_configured(
    store: Any,
    workspace_id: str,
    env_keys: tuple[str, ...],
) -> bool:
    if not env_keys:
        return True
    # All keys in the tuple are required (AND). Env names may be OR alternatives
    # within a slot; adapters pass OR lists as separate keys in one tuple meaning AND of slots.
    # Existing adapters use OR env names for the same secret. Treat any present as enough
    # when they map to the same slot; otherwise require each distinct slot.
    needed_slots: set[str] = set()
    unmatched: list[str] = []
    for name in env_keys:
        slot = _SLOT_BY_ENV.get(name)
        if slot:
            needed_slots.add(slot.slot_id)
        else:
            unmatched.append(name)
    for slot_id in needed_slots:
        if not get_slot_value(store, workspace_id, slot_id):
            return False
    for name in unmatched:
        if not _env(name):
            return False
    return True if needed_slots or unmatched else True
