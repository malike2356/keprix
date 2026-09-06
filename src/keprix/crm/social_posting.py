"""Social organic posting connectors (prompt 07) - decision-gated.

Composition and scheduling already exist (personas/prism/social.py build_calendar,
agent_os/workflows/content_series.py, personas/beacon/campaign.py). Nothing publishes.
This module adds the publish boundary: a PostPublisher protocol and per-platform
adapters that return honest states (published with external_post_id + public_url,
not_configured, pending_approval, or unsupported). No live HTTP is performed until a
provider decision is recorded; this is the interface + fixtures + readiness layer.

Scopes are per-platform and verified, never self-granted. xAI search credentials
(XAI_API_KEY) and X Developer Platform posting credentials (X_API_* / tweet.write)
are strictly separate.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from keprix.crm.store import CrmStore


def _utcnow() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


# Per-platform required scopes (verified, never self-granted).
POSTING_SCOPES: dict[str, tuple[str, ...]] = {
    "meta": ("pages_manage_posts", "pages_read_engagement"),
    "linkedin": ("w_member_social",),  # Community Management API; dev review required
    "x": ("tweet.write", "tweet.read"),
}

# Decision-gated: none approved yet. Mirrors crm/social_channels PROVIDERS matrix.
POSTING_DECISIONS: dict[str, dict[str, Any]] = {
    "meta": {"provider": "meta_graph", "decision": "pending", "endpoint": "POST /{page-id}/feed"},
    "linkedin": {"provider": "sendpilot", "decision": "pending", "endpoint": "provider posting"},
    "x": {"provider": "x_api", "decision": "pending", "endpoint": "POST /2/tweets"},
}


class PostPublisher(Protocol):
    def publish(
        self, text: str, media_url: str | None = None, *, workspace_id: str | None = None
    ) -> dict[str, Any]: ...


def _publish_result(
    channel: str,
    *,
    status: str,
    external_post_id: str = "",
    public_url: str = "",
    reason: str = "",
) -> dict[str, Any]:
    return {
        "channel": channel,
        "status": status,
        "external_post_id": external_post_id,
        "public_url": public_url,
        "reason": reason,
        "published_at": _utcnow() if status == "published" else "",
    }


def posting_configured(channel: str) -> bool:
    info = POSTING_DECISIONS.get(channel)
    return bool(info and info.get("decision") == "approved")


def _has_credentials(channel: str, workspace_id: str | None = None) -> bool:
    from keprix.crm.connections import resolve_any

    keys: dict[str, tuple[str, ...]] = {
        "meta": ("META_APP_ID", "META_APP_SECRET"),
        "linkedin": ("LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET"),
        "x": ("X_API_KEY", "X_API_SECRET"),  # Developer Platform, NOT XAI_API_KEY
    }
    names = keys.get(channel, ())
    return all(bool(resolve_any(n, workspace_id=workspace_id)) for n in names)


def publish(
    channel: str, text: str, media_url: str | None = None, *, workspace_id: str | None = None
) -> dict[str, Any]:
    """Publish to a social channel. Honest state; never a fabricated post id."""
    channel = (channel or "").strip().lower()
    if channel not in POSTING_DECISIONS:
        return _publish_result(channel, status="unsupported", reason=f"unknown channel {channel!r}")

    if not posting_configured(channel):
        info = POSTING_DECISIONS[channel]
        status = "pending_approval" if info.get("decision") == "pending" else "not_configured"
        return _publish_result(
            channel,
            status=status,
            reason=f"{channel} posting is gated on an owner-approved provider decision",
        )

    if not _has_credentials(channel, workspace_id):
        return _publish_result(
            channel, status="not_configured", reason=f"{channel} credentials missing"
        )

    # A provider is approved and credentials present, but no live adapter is wired
    # (no provider decision recorded yet in practice). Return honest unsupported
    # rather than a fabricated success.
    return _publish_result(
        channel,
        status="unsupported",
        reason=f"{channel} live publish adapter not yet wired (provider decision required)",
    )


class MetaGraphPublisher:
    channel = "meta"

    def publish(
        self, text: str, media_url: str | None = None, *, workspace_id: str | None = None
    ) -> dict[str, Any]:
        return publish(self.channel, text, media_url, workspace_id=workspace_id)


class LinkedInPublisher:
    channel = "linkedin"

    def publish(
        self, text: str, media_url: str | None = None, *, workspace_id: str | None = None
    ) -> dict[str, Any]:
        return publish(self.channel, text, media_url, workspace_id=workspace_id)


class XPublisher:
    channel = "x"

    def publish(
        self, text: str, media_url: str | None = None, *, workspace_id: str | None = None
    ) -> dict[str, Any]:
        return publish(self.channel, text, media_url, workspace_id=workspace_id)


PUBLISHERS: dict[str, PostPublisher] = {
    "meta": MetaGraphPublisher(),
    "linkedin": LinkedInPublisher(),
    "x": XPublisher(),
}


def record_publish_result(
    store: CrmStore,
    workspace_id: str,
    channel: str,
    result: dict[str, Any],
    *,
    scheduled_post_id: str = "",
) -> dict[str, Any]:
    """Persist a per-platform publish result so a failure never corrupts the schedule."""
    ws = store._require_workspace(workspace_id)
    now = _utcnow()
    row_id = f"sp_{uuid.uuid4().hex[:16]}"
    store._conn.execute(
        "INSERT INTO crm_social_events "
        "(id, workspace_id, channel, provider_event_id, event_type, payload_json, lead_id, processed, created_at) "
        "VALUES (?, ?, ?, ?, 'post_publish', ?, '', 1, ?)",
        (
            row_id,
            ws,
            channel,
            result.get("external_post_id") or f"local:{row_id}",
            json.dumps({"result": result, "scheduled_post_id": scheduled_post_id}),
            now,
        ),
    )
    store._conn.commit()
    return {"ok": True, "id": row_id, "status": result.get("status")}


def supported_scopes() -> dict[str, list[str]]:
    return {k: list(v) for k, v in POSTING_SCOPES.items()}
