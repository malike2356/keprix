"""Honest capability health for Customer Concierge (Prompt 629).

Reports ``not_configured`` when credentials or env are absent. Never claims
Zoom create, Microsoft calendar write, or delivery proof that do not exist.
"""

from __future__ import annotations

import os
from typing import Any

from keprix.customer_concierge.contract_types import (
    CUSTOMER_CONCIERGE_CONTRACT_VERSION,
    ConciergeFeatureKey,
    ConciergeReadinessReport,
    FeatureReadinessStatus,
    as_feature,
)
from keprix.customer_concierge.scope import resolve_scope
from keprix.customer_concierge.store import get_concierge_store


def _env_flag(name: str, default_on: bool = True) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if not raw:
        return default_on
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    return default_on


def concierge_feature_flags() -> dict[ConciergeFeatureKey, bool]:
    return {
        "publicConcierge": _env_flag("KEPRIX_CONCIERGE_PUBLIC_ENABLED", True),
        "zoom": _env_flag("KEPRIX_CONCIERGE_ZOOM_ENABLED", True),
        "googleCalendar": _env_flag("KEPRIX_CONCIERGE_GOOGLE_CALENDAR_ENABLED", True),
        "microsoftCalendar": _env_flag("KEPRIX_CONCIERGE_MICROSOFT_CALENDAR_ENABLED", True),
        "emailDelivery": _env_flag("KEPRIX_CONCIERGE_EMAIL_DELIVERY_ENABLED", True),
        "inboundWebhookReconciliation": _env_flag("KEPRIX_CONCIERGE_INBOUND_WEBHOOKS_ENABLED", True),
    }


def _persistence_mode() -> str:
    """Community Edition local SQLite vs hosted Postgres (honest label only)."""
    try:
        from keprix.crm.durable import postgres_engine_configured, resolve_crm_backend

        if resolve_crm_backend() == "postgres" and postgres_engine_configured():
            return "postgres"
    except Exception:
        pass
    url = (os.environ.get("KEPRIX_DATABASE_URL") or "").strip()
    if url and "postgres" in url.lower() and "pytest" not in os.environ.get("PYTEST_CURRENT_TEST", ""):
        return "postgres"
    return "sqlite"


def _zoom_status() -> tuple[FeatureReadinessStatus, str]:
    # Conferencing helper is URL/template only; Zoom create is Prompt 632.
    client = (os.environ.get("ZOOM_CLIENT_ID") or "").strip()
    secret = (os.environ.get("ZOOM_CLIENT_SECRET") or "").strip()
    if not client or not secret:
        return "not_configured", "ZOOM_CLIENT_ID/SECRET missing; meeting create not implemented (URL template only)"
    return "disconnected", "Zoom OAuth env present; no managed meeting create/reconcile yet"


def _google_calendar_status() -> tuple[FeatureReadinessStatus, str]:
    if not (
        (os.environ.get("GOOGLE_CLIENT_ID") or os.environ.get("GOOGLE_OAUTH_CLIENT_ID") or "").strip()
        and (os.environ.get("GOOGLE_CLIENT_SECRET") or os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET") or "").strip()
    ):
        return "not_configured", "Google Calendar OAuth not configured"
    return "disconnected", "Google OAuth env present; concierge calendar projection not wired"


def _microsoft_calendar_status() -> tuple[FeatureReadinessStatus, str]:
    return "not_configured", "Microsoft Graph calendar driver not live"


def _email_delivery_status() -> tuple[FeatureReadinessStatus, str]:
    if (
        (os.environ.get("SENDGRID_API_KEY") or "").strip()
        or (os.environ.get("MAILGUN_API_KEY") or "").strip()
        or (os.environ.get("SMTP_URL") or "").strip()
        or (os.environ.get("KEPRIX_OUTREACH_FROM_EMAIL") or "").strip()
    ):
        # viCal default outbox is in-memory; not proof of delivery
        return "disconnected", "Outbound email env present; viCal notification outbox is not delivery proof"
    return "not_configured", "Outbound email provider not configured; viCal uses in-memory outbox"


def _inbound_webhook_status() -> tuple[FeatureReadinessStatus, str]:
    if (
        (os.environ.get("KEPRIX_CONCIERGE_ZOOM_WEBHOOK_SECRET") or "").strip()
        or (os.environ.get("ZOOM_WEBHOOK_SECRET") or "").strip()
        or (os.environ.get("KEPRIX_CONCIERGE_GOOGLE_CALENDAR_WEBHOOK_TOKEN") or "").strip()
    ):
        return "disconnected", "Webhook secret present; inbound reconcile not implemented"
    return "not_configured", "Provider inbound webhook receivers not configured"


def evaluate_capability_health(
    *,
    workspace_id: str | None = None,
    persona_id: str = "default",
    user_id: str | None = None,
) -> dict[str, Any]:
    scope = resolve_scope(workspace_id=workspace_id, user_id=user_id, persona_id=persona_id)
    flags = concierge_feature_flags()
    profile = None
    try:
        profile = get_concierge_store().get(scope.workspace_id, scope.persona_id)
    except Exception:
        profile = None

    if profile and profile.published:
        public_status: FeatureReadinessStatus = "ready"
        public_detail = "Published concierge profile"
    elif profile:
        public_status = "disconnected"
        public_detail = "Concierge profile exists but unpublished"
    else:
        public_status = "not_configured"
        public_detail = "No concierge profile"

    zoom_s, zoom_d = _zoom_status()
    google_s, google_d = _google_calendar_status()
    ms_s, ms_d = _microsoft_calendar_status()
    email_s, email_d = _email_delivery_status()
    hook_s, hook_d = _inbound_webhook_status()

    features = {
        "publicConcierge": as_feature(
            "publicConcierge", enabled=flags["publicConcierge"], status=public_status, detail=public_detail
        ),
        "zoom": as_feature("zoom", enabled=flags["zoom"], status=zoom_s, detail=zoom_d),
        "googleCalendar": as_feature(
            "googleCalendar", enabled=flags["googleCalendar"], status=google_s, detail=google_d
        ),
        "microsoftCalendar": as_feature(
            "microsoftCalendar", enabled=flags["microsoftCalendar"], status=ms_s, detail=ms_d
        ),
        "emailDelivery": as_feature(
            "emailDelivery", enabled=flags["emailDelivery"], status=email_s, detail=email_d
        ),
        "inboundWebhookReconciliation": as_feature(
            "inboundWebhookReconciliation",
            enabled=flags["inboundWebhookReconciliation"],
            status=hook_s,
            detail=hook_d,
        ),
    }

    blockers = [
        key
        for key, feat in features.items()
        if feat["enabled"] and feat["status"] in {"not_configured", "error", "disconnected"}
        and key != "publicConcierge"
    ]
    # publicConcierge ready alone does not make managed Zoom booking ready
    if features["publicConcierge"]["status"] != "ready":
        blockers.insert(0, "publicConcierge")

    report: ConciergeReadinessReport = {
        "contractVersion": CUSTOMER_CONCIERGE_CONTRACT_VERSION,
        "workspaceId": scope.workspace_id,
        "conciergeId": profile.id if profile else None,
        "ready": False,  # managed Zoom booking not complete until 632+
        "features": features,
        "blockers": blockers,
    }

    return {
        **report,
        "scope": {
            "workspaceId": scope.workspace_id,
            "tenantId": scope.tenant_id,
            "userId": scope.user_id,
            "personaId": scope.persona_id,
        },
        "persistenceMode": _persistence_mode(),
        "honesty": [
            "Meeting URL templates are not managed Zoom booking.",
            "viCal notification outbox is in-memory and is not proof of delivery.",
            "Operator /api/support routes are not external customer support.",
            "Capability ready=false until conferencing create, calendar projection, and delivery proof exist.",
        ],
        "gaps": [
            "zoom_meeting_create",
            "microsoft_calendar_driver",
            "durable_notification_delivery",
            "external_customer_support_api",
            "audience_session_principal",
            "inbound_provider_webhook_reconcile",
        ],
    }
