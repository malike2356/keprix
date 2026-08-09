"""Customer Concierge v1 contract constants and types (Prompt 629)."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

CUSTOMER_CONCIERGE_CONTRACT_VERSION = "1.0.0"
CARINA_RUNTIME_REQUIRED = False

ActorType = Literal["audience", "operator", "system", "provider"]
BookingState = Literal[
    "held",
    "pending_confirmation",
    "provisioning",
    "confirmed",
    "action_required",
    "rescheduling",
    "cancelled",
    "completed",
    "no_show",
]
DeliveryState = Literal[
    "pending",
    "sent",
    "delivered",
    "accepted",
    "declined",
    "failed",
    "unknown",
]
FeatureReadinessStatus = Literal[
    "ready",
    "not_configured",
    "disconnected",
    "error",
    "disabled",
]
ConciergeFeatureKey = Literal[
    "publicConcierge",
    "zoom",
    "googleCalendar",
    "microsoftCalendar",
    "emailDelivery",
    "inboundWebhookReconciliation",
]

BOOKING_STATES: tuple[str, ...] = (
    "held",
    "pending_confirmation",
    "provisioning",
    "confirmed",
    "action_required",
    "rescheduling",
    "cancelled",
    "completed",
    "no_show",
)
DELIVERY_STATES: tuple[str, ...] = (
    "pending",
    "sent",
    "delivered",
    "accepted",
    "declined",
    "failed",
    "unknown",
)
ACTOR_TYPES: tuple[str, ...] = ("audience", "operator", "system", "provider")
PROVIDER_NAMES: tuple[str, ...] = (
    "google_calendar",
    "microsoft_calendar",
    "zoom",
    "email",
    "sms",
)


class FeatureStatus(TypedDict):
    key: str
    enabled: bool
    status: FeatureReadinessStatus
    detail: str | None


class ConciergeReadinessReport(TypedDict):
    contractVersion: str
    workspaceId: str
    conciergeId: str | None
    ready: bool
    features: dict[str, FeatureStatus]
    blockers: list[str]


def as_feature(
    key: ConciergeFeatureKey,
    *,
    enabled: bool,
    status: FeatureReadinessStatus,
    detail: str | None,
) -> FeatureStatus:
    if not enabled:
        return {"key": key, "enabled": False, "status": "disabled", "detail": "Feature flag disabled"}
    return {"key": key, "enabled": True, "status": status, "detail": detail}
