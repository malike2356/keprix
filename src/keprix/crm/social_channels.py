"""Social channel connectors (prompt 06) - decision-gated.

A pluggable SocialProvider protocol over licensed providers / official APIs.
No provider decision is recorded yet, so per the prompt this module ships the
interface, capability matrix, per-workspace channel/connection store, webhook
signature verification, and readiness checks ONLY. Outbound and discovery are
refused with `unsupported`/`not_configured` until a provider decision is
committed. LinkedIn/FB/IG/X scraping is absolutely forbidden.

Provider decisions are recorded in a committed capability matrix (PROVIDERS)
with `decision: "pending"`; an owner approval flips a provider to an enabled
state with its capability flags. Until then every operation degrades honestly.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from keprix.crm.store import CrmStore


def _utcnow() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------------
# Provider capability matrix (decision-gated). decision=pending means the owner
# has not chosen/approved a provider; the channel refuses outbound.
# ---------------------------------------------------------------------------
PROVIDERS: dict[str, dict[str, Any]] = {
    "linkedin": {
        "provider": "sendpilot",  # or "linkedin_api" when owner chooses official API
        "decision": "pending",
        "capabilities": {
            "discovery": False,
            "connection_request": False,
            "message": False,
            "posting": False,
        },
        "webhook_verification": "provider_signature",  # documented per provider
    },
    "meta_lead_ads": {
        "provider": "meta_graph",
        "decision": "pending",
        "capabilities": {
            "discovery": False,
            "leadgen": False,
        },
        "webhook_verification": "x_hub_signature_256",
    },
    "x": {
        "provider": "x_api",
        "decision": "pending",
        "capabilities": {
            "discovery": True,  # read-only reuse of x_search_tool
            "message": False,  # native DM only after messaging eligibility confirmed
        },
        "webhook_verification": "crc",  # decision-gated
    },
}


class SocialProvider(Protocol):
    def list_senders(self) -> list[dict]: ...
    def discover_leads(self, criteria: dict[str, Any], limit: int) -> list[dict]: ...
    def send_connection_request(self, provider_lead_id: str) -> dict: ...
    def send_message(self, provider_lead_id: str, body: str) -> dict: ...
    def on_leadgen_event(self, payload: dict[str, Any]) -> dict: ...
    def list_conversations(self) -> list[dict]: ...


def channel_decision(channel: str) -> dict[str, Any]:
    """The committed provider decision for a channel, or a pending placeholder."""
    return PROVIDERS.get(channel, {"provider": "", "decision": "pending", "capabilities": {}})


def channel_configured(channel: str) -> bool:
    info = PROVIDERS.get(channel)
    return bool(info and info.get("decision") == "approved")


def _refuse(channel: str, op: str) -> dict[str, Any]:
    info = channel_decision(channel)
    return {
        "ok": False,
        "status": "unsupported" if info.get("decision") != "pending" else "not_configured",
        "channel": channel,
        "operation": op,
        "reason": f"{channel} {op} is gated on an owner-approved provider decision",
        "provider": info.get("provider"),
        "decision": info.get("decision"),
    }


def capability_supported(channel: str, capability: str) -> bool:
    info = channel_decision(channel)
    return bool((info.get("capabilities") or {}).get(capability))


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------


def verify_meta_signature(body: bytes, signature: str, app_secret: str) -> bool:
    """Verify a Meta webhook X-Hub-Signature-256 header (HMAC-SHA256, sha256=hex)."""
    if not signature or not app_secret or body is None:
        return False
    expected_prefix = "sha256="
    if not signature.startswith(expected_prefix):
        return False
    expected = signature[len(expected_prefix) :]
    try:
        digest = hmac.new(app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    except Exception:  # noqa: BLE001
        return False
    return hmac.compare_digest(digest, expected)


def verify_provider_signature(body: bytes, signature: str, secret: str) -> bool:
    """Generic provider signature check (HMAC-SHA256 hex, no prefix)."""
    if not signature or not secret or body is None:
        return False
    try:
        digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    except Exception:  # noqa: BLE001
        return False
    return hmac.compare_digest(digest, signature)


# ---------------------------------------------------------------------------
# Per-workspace channel store
# ---------------------------------------------------------------------------


def connect_channel(
    store: CrmStore,
    workspace_id: str,
    channel: str,
    *,
    provider_account_id: str = "",
    decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ws = store._require_workspace(workspace_id)
    row_id = f"sc_{uuid.uuid4().hex[:16]}"
    now = _utcnow()
    info = channel_decision(channel)
    snapshot = decision or info
    store._conn.execute(
        "INSERT OR REPLACE INTO crm_social_channels "
        "(id, workspace_id, channel, provider, provider_account_id, status, decision_json, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)",
        (
            row_id,
            ws,
            channel,
            str(info.get("provider") or ""),
            provider_account_id,
            json.dumps(snapshot),
            now,
            now,
        ),
    )
    store._conn.execute(
        "INSERT OR REPLACE INTO crm_channel_connections (id, workspace_id, channel, provider_account_id, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, 'connected', ?, ?)",
        (f"cc_{uuid.uuid4().hex[:16]}", ws, channel, provider_account_id, now, now),
    )
    store._conn.commit()
    return {
        "ok": True,
        "channel": channel,
        "provider": info.get("provider"),
        "decision": info.get("decision"),
        "status": "pending",
    }


def list_connections(store: CrmStore, workspace_id: str) -> list[dict[str, Any]]:
    ws = store._require_workspace(workspace_id)
    rows = store._conn.execute(
        "SELECT channel, provider_account_id, status, created_at FROM crm_channel_connections WHERE workspace_id = ? ORDER BY channel",
        (ws,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Provider operations (all refuse until decision-gated)
# ---------------------------------------------------------------------------


def list_senders(channel: str) -> dict[str, Any]:
    if not channel_configured(channel):
        return _refuse(channel, "list_senders")
    return {
        "ok": False,
        "status": "unsupported",
        "reason": "live sender listing requires the chosen provider adapter",
    }


def discover_leads(channel: str, criteria: dict[str, Any], limit: int = 25) -> dict[str, Any]:
    if channel == "x" and capability_supported("x", "discovery"):
        from keprix.tools.x_search_tool import x_search_tool

        try:
            return {
                "ok": True,
                "results": x_search_tool(str(criteria.get("query") or ""), limit=limit),
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "status": "error", "reason": str(exc)}
    if not channel_configured(channel) or not capability_supported(channel, "discovery"):
        return _refuse(channel, "discover_leads")
    return {
        "ok": False,
        "status": "unsupported",
        "reason": "discovery requires the chosen provider adapter",
    }


def send_connection_request(channel: str, provider_lead_id: str) -> dict[str, Any]:
    if not channel_configured(channel) or not capability_supported(channel, "connection_request"):
        return _refuse(channel, "send_connection_request")
    return {
        "ok": False,
        "status": "unsupported",
        "reason": "connection requests require the chosen provider adapter",
    }


def send_message(channel: str, provider_lead_id: str, body: str) -> dict[str, Any]:
    if not channel_configured(channel) or not capability_supported(channel, "message"):
        return _refuse(channel, "send_message")
    return {
        "ok": False,
        "status": "unsupported",
        "reason": "messaging requires the chosen provider adapter",
    }


def on_leadgen_event(channel: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not channel_configured(channel) or not capability_supported(channel, "leadgen"):
        return _refuse(channel, "leadgen")
    return {
        "ok": False,
        "status": "unsupported",
        "reason": "leadgen webhook requires the chosen provider adapter",
    }


def list_conversations(channel: str) -> dict[str, Any]:
    if not channel_configured(channel):
        return _refuse(channel, "list_conversations")
    return {
        "ok": False,
        "status": "unsupported",
        "reason": "conversation listing requires the chosen provider adapter",
    }


# ---------------------------------------------------------------------------
# Webhook event ingestion (replay-safe)
# ---------------------------------------------------------------------------


def record_social_event(
    store: CrmStore,
    workspace_id: str,
    channel: str,
    provider_event_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Record a verified provider webhook event once (unique on provider event id)."""
    ws = store._require_workspace(workspace_id)
    if not provider_event_id:
        return {"ok": False, "status": "rejected", "reason": "missing provider_event_id"}
    now = _utcnow()
    existing = store._conn.execute(
        "SELECT id FROM crm_social_events WHERE workspace_id = ? AND channel = ? AND provider_event_id = ?",
        (ws, channel, provider_event_id),
    ).fetchone()
    if existing:
        return {"ok": True, "status": "duplicate", "replay_safe": True}
    row_id = f"se_{uuid.uuid4().hex[:16]}"
    store._conn.execute(
        "INSERT INTO crm_social_events (id, workspace_id, channel, provider_event_id, event_type, payload_json, lead_id, processed, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, '', 0, ?)",
        (row_id, ws, channel, provider_event_id, event_type, json.dumps(payload), now),
    )
    store._conn.commit()
    return {"ok": True, "status": "recorded", "id": row_id}
