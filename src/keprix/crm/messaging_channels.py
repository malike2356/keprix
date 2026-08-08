"""WhatsApp Business and SMS outbound after channel consent (prompt 459)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.crm.compliance import evaluate_send_policy
from keprix.crm.data_quality import get_nice_settings, upsert_nice_settings
from keprix.crm.nice_schema import ensure_nice_schema
from keprix.crm.soft_wall import gate_or_approve

WHATSAPP_SMS_FLAG = "KEPRIX_WHATSAPP_SMS"
STOP_KEYWORDS = frozenset({"stop", "unsubscribe", "cancel", "end", "quit"})


def channel_flag_enabled(workspace_id: str | None = None) -> bool:
    if workspace_id:
        try:
            from keprix.crm.connections import workspace_flag_enabled
            from keprix.crm.store import get_crm_store

            if workspace_flag_enabled(get_crm_store(), workspace_id, "whatsapp_sms_enabled"):
                return True
        except Exception:
            pass
    raw = os.environ.get(WHATSAPP_SMS_FLAG, "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def _resolve(workspace_id: str | None, *names: str) -> str:
    if workspace_id:
        try:
            from keprix.crm.connections import resolve_any
            from keprix.crm.store import get_crm_store

            return resolve_any(*names, workspace_id=workspace_id, store=get_crm_store())
        except Exception:
            pass
    return _env(*names)


def provider_status(workspace_id: str | None = None) -> dict[str, Any]:
    wa = bool(_resolve(workspace_id, "KEPRIX_WHATSAPP_TOKEN", "WHATSAPP_TOKEN", "META_WHATSAPP_TOKEN"))
    sms = bool(_resolve(workspace_id, "KEPRIX_TWILIO_AUTH_TOKEN", "TWILIO_AUTH_TOKEN"))
    sid = bool(_resolve(workspace_id, "KEPRIX_TWILIO_ACCOUNT_SID", "TWILIO_ACCOUNT_SID"))
    return {
        "feature_flag": WHATSAPP_SMS_FLAG,
        "flag_enabled": channel_flag_enabled(workspace_id),
        "configure_path": "/crm/settings#connections",
        "whatsapp": {
            "configured": wa,
            "status": "ready" if wa else "not_configured",
            "required_env": ["KEPRIX_WHATSAPP_TOKEN"],
            "slots": ["whatsapp_token", "whatsapp_phone_number_id"],
        },
        "sms": {
            "configured": sms and sid,
            "status": "ready" if (sms and sid) else "not_configured",
            "required_env": ["KEPRIX_TWILIO_AUTH_TOKEN", "KEPRIX_TWILIO_ACCOUNT_SID"],
            "slots": ["twilio_auth_token", "twilio_account_sid", "twilio_from_number"],
        },
    }


def register_template(
    store: Any,
    workspace_id: str,
    *,
    channel: str,
    name: str,
    body: str,
    provider_template_id: str | None = None,
    actor_id: str | None = None,
    force: bool = False,
    approval_id: str | None = None,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    gate = gate_or_approve(
        ws,
        kind="channel_template_approve",
        subject=f"Approve {channel} template {name}",
        payload={"channel": channel, "name": name, "provider_template_id": provider_template_id},
        object_type="channel_template",
        object_id=name,
        actor_id=actor_id,
        force=force,
        approval_id=approval_id,
    )
    if gate.get("blocked"):
        return {"ok": False, "blocked": True, "approval": gate.get("approval")}
    rid = str(uuid.uuid4())
    now = _utcnow()
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO crm_channel_templates (
                id, workspace_id, channel, name, provider_template_id, body, approved, actor_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (rid, ws, channel, name, provider_template_id, body, actor_id, now, now),
        )
        store._conn.commit()
    return {"ok": True, "template": store._fetchone("SELECT * FROM crm_channel_templates WHERE id = ?", (rid,))}


def list_templates(store: Any, workspace_id: str, *, channel: str | None = None) -> list[dict[str, Any]]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    if channel:
        return store._fetchall(
            "SELECT * FROM crm_channel_templates WHERE workspace_id = ? AND channel = ?",
            (ws, channel),
        )
    return store._fetchall(
        "SELECT * FROM crm_channel_templates WHERE workspace_id = ?",
        (ws,),
    )


def _has_channel_consent(store: Any, workspace_id: str, *, subject_type: str, subject_id: str, channel: str) -> bool:
    rows = store.list_consent_records(workspace_id)
    for row in rows:
        if row.get("subject_type") != subject_type or row.get("subject_id") != subject_id:
            continue
        if row.get("channel") != channel:
            continue
        if row.get("withdrawn_at"):
            continue
        return True
    return False


def send_channel_message(
    store: Any,
    workspace_id: str,
    *,
    channel: str,
    subject_type: str,
    subject_id: str,
    address: str,
    template_id: str | None = None,
    body: str | None = None,
    actor_id: str | None = None,
    force: bool = False,
    approval_id: str | None = None,
    first_touch: bool = True,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    channel = channel.lower().strip()
    if channel not in {"sms", "whatsapp"}:
        return {"ok": False, "error": "unsupported_channel"}

    if not channel_flag_enabled(ws):
        return {
            "ok": False,
            "error": "feature_flag_off",
            "message": f"{WHATSAPP_SMS_FLAG} is off. Enable under /crm/settings Connections (or env), then Soft Wall enable.",
            "status": provider_status(ws),
            "configure_path": "/crm/settings#connections",
        }

    settings = get_nice_settings(store, ws)
    if not settings.get("whatsapp_sms_enabled"):
        return {
            "ok": False,
            "error": "workspace_channel_disabled",
            "message": "Workspace WhatsApp/SMS toggle is off under Soft Wall settings.",
        }

    status = provider_status(ws)
    if channel == "whatsapp" and not status["whatsapp"]["configured"]:
        return {"ok": False, "status": "not_configured", "provider": status["whatsapp"]}
    if channel == "sms" and not status["sms"]["configured"]:
        return {"ok": False, "status": "not_configured", "provider": status["sms"]}

    if not _has_channel_consent(store, ws, subject_type=subject_type, subject_id=subject_id, channel=channel):
        return {
            "ok": False,
            "error": "missing_channel_consent",
            "message": f"No {channel} consent; email consent alone is insufficient.",
        }

    policy = evaluate_send_policy(
        store,
        ws,
        subject_type=subject_type,
        subject_id=subject_id,
        channel=channel,
        address=address,
    )
    if policy.get("decision") == "deny":
        return {"ok": False, "error": "suppressed_or_denied", "policy": policy}

    template = None
    if template_id:
        template = store._fetchone(
            "SELECT * FROM crm_channel_templates WHERE workspace_id = ? AND id = ?",
            (ws, template_id),
        )
        if not template or not template.get("approved"):
            return {"ok": False, "error": "template_unapproved"}

    if first_touch:
        gate = gate_or_approve(
            ws,
            kind="first_whatsapp_sms_send",
            subject=f"First {channel} send to {address}",
            payload={
                "channel": channel,
                "subject_type": subject_type,
                "subject_id": subject_id,
                "address": address,
                "template_id": template_id,
            },
            object_type=subject_type,
            object_id=subject_id,
            actor_id=actor_id,
            force=force,
            approval_id=approval_id,
            always_require=True,
        )
        if gate.get("blocked"):
            return {"ok": False, "blocked": True, "approval": gate.get("approval")}

    text = body or (template or {}).get("body") or ""
    # Honest stub send: record activity, do not invent delivery.
    activity = store.create_activity(
        ws,
        entity_type=subject_type,
        entity_id=subject_id,
        activity_type=f"{channel}_outbound",
        channel=channel,
        subject=f"{channel} message",
        body=text,
        metadata={
            "provider_status": "queued_stub",
            "template_id": template_id,
            "address": address,
            "official_api_only": True,
        },
        actor_type="user",
        actor_id=actor_id,
    )
    return {"ok": True, "activity": activity, "mode": "official_api_stub"}


def handle_inbound_stop(
    store: Any,
    workspace_id: str,
    *,
    channel: str,
    address: str,
    body: str,
    subject_type: str | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    text = (body or "").strip().lower()
    if text not in STOP_KEYWORDS and not any(k in text.split() for k in STOP_KEYWORDS):
        return {"ok": True, "suppressed": False}
    store.create_suppression_entry(
        workspace_id,
        channel=channel,
        address=address,
        reason="stop_keyword",
        source="inbound",
        subject_type=subject_type,
        subject_id=subject_id,
    )
    return {"ok": True, "suppressed": True, "reason": "stop_keyword"}


def enable_workspace_channels(
    store: Any,
    workspace_id: str,
    *,
    enabled: bool,
    actor_id: str | None = None,
    force: bool = False,
    approval_id: str | None = None,
) -> dict[str, Any]:
    if enabled and not channel_flag_enabled(workspace_id):
        return {
            "ok": False,
            "error": "feature_flag_off",
            "status": provider_status(workspace_id),
            "configure_path": "/crm/settings#connections",
        }
    if enabled:
        gate = gate_or_approve(
            workspace_id,
            kind="whatsapp_sms_enable",
            subject="Enable WhatsApp/SMS channels",
            payload={"enabled": True},
            object_type="settings",
            object_id="whatsapp_sms",
            actor_id=actor_id,
            force=force,
            approval_id=approval_id,
        )
        if gate.get("blocked"):
            return {"ok": False, "blocked": True, "approval": gate.get("approval")}
    settings = upsert_nice_settings(store, workspace_id, whatsapp_sms_enabled=enabled)
    return {"ok": True, "settings": settings, "status": provider_status(workspace_id)}
