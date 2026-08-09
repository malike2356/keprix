"""Pydantic validators for Customer Concierge v1 fixtures (Prompt 629).

Aligned with ``contracts/customer-concierge-v1/schemas``. No Carina imports.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from keprix.customer_concierge.contract_types import (
    ACTOR_TYPES,
    CUSTOMER_CONCIERGE_CONTRACT_VERSION,
    PROVIDER_NAMES,
)

ActorType = Literal["audience", "operator", "system", "provider"]
ProviderName = Literal["google_calendar", "microsoft_calendar", "zoom", "email", "sms"]
ProviderResultStatus = Literal[
    "succeeded",
    "failed",
    "retryable",
    "action_required",
    "not_configured",
    "duplicate",
]
DeliveryState = Literal["pending", "sent", "delivered", "accepted", "declined", "failed", "unknown"]
FeatureStatusEnum = Literal["ready", "not_configured", "disconnected", "error", "disabled"]
MachineName = Literal["booking", "delivery", "support_case", "audience_session"]
DomainObjectType = Literal["audience_identity", "audience_session", "booking", "support_case"]


class EventEnvelopeModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    contractVersion: Literal["1.0.0"]
    eventId: str = Field(min_length=1)
    eventType: str = Field(min_length=1)
    occurredAt: str = Field(min_length=1)
    workspaceId: str = Field(min_length=1)
    conciergeId: str = Field(min_length=1)
    correlationId: str = Field(min_length=1)
    causationId: str = Field(min_length=1)
    actorType: ActorType
    actorId: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ProviderCommandModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    contractVersion: Literal["1.0.0"]
    commandId: str = Field(min_length=1)
    provider: ProviderName
    action: str = Field(min_length=1)
    workspaceId: str = Field(min_length=1)
    conciergeId: str | None = None
    actorType: ActorType
    idempotencyKey: str = Field(min_length=1)
    payload: dict[str, Any] | None = None


class ProviderResultModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    contractVersion: Literal["1.0.0"]
    commandId: str = Field(min_length=1)
    provider: ProviderName
    workspaceId: str = Field(min_length=1)
    actorType: ActorType
    ok: bool
    status: ProviderResultStatus
    providerResourceId: str | None = None
    joinUrl: str | None = None
    deliveryState: DeliveryState | None = None
    errorCode: str | None = None
    errorMessage: str | None = None


class StateTransitionModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    contractVersion: Literal["1.0.0"]
    machine: MachineName
    from_: str = Field(alias="from", min_length=1)
    to: str = Field(min_length=1)
    workspaceId: str = Field(min_length=1)
    actorType: ActorType
    entityId: str | None = None
    reason: str | None = None


class FeatureStatusModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: str = Field(min_length=1)
    enabled: bool
    status: FeatureStatusEnum
    detail: str | None = None


class ReadinessFeaturesModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    publicConcierge: FeatureStatusModel
    zoom: FeatureStatusModel
    googleCalendar: FeatureStatusModel
    microsoftCalendar: FeatureStatusModel
    emailDelivery: FeatureStatusModel
    inboundWebhookReconciliation: FeatureStatusModel


class ReadinessReportModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    contractVersion: Literal["1.0.0"]
    workspaceId: str = Field(min_length=1)
    conciergeId: str | None
    ready: bool
    features: ReadinessFeaturesModel
    blockers: list[str]


class DomainObjectInnerModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    workspaceId: str = Field(min_length=1)
    actorType: ActorType


class DomainWrapperModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    objectType: DomainObjectType
    object: DomainObjectInnerModel


def assert_mandatory_tenant_and_actor(value: dict[str, Any]) -> None:
    wid = value.get("workspaceId")
    if not isinstance(wid, str) or not wid.strip():
        raise ValueError("workspaceId (tenant id) is mandatory")
    actor = value.get("actorType")
    if not isinstance(actor, str) or actor not in ACTOR_TYPES:
        raise ValueError("actorType is mandatory")


def parse_event_envelope(data: Any) -> EventEnvelopeModel:
    return EventEnvelopeModel.model_validate(data)


def parse_provider_command(data: Any) -> ProviderCommandModel:
    return ProviderCommandModel.model_validate(data)


def parse_provider_result(data: Any) -> ProviderResultModel:
    return ProviderResultModel.model_validate(data)


def parse_state_transition(data: Any) -> StateTransitionModel:
    return StateTransitionModel.model_validate(data)


def parse_readiness_report(data: Any) -> ReadinessReportModel:
    return ReadinessReportModel.model_validate(data)


def parse_domain_wrapper(data: Any) -> DomainWrapperModel:
    return DomainWrapperModel.model_validate(data)


def validate_fixture_file(name: str, data: Any) -> Any:
    """Validate a synthetic fixture by filename convention (Carina parity)."""
    if name.startswith("event-"):
        parsed = parse_event_envelope(data)
        assert_mandatory_tenant_and_actor(parsed.model_dump())
        return parsed
    if name.startswith("domain-"):
        parsed = parse_domain_wrapper(data)
        assert_mandatory_tenant_and_actor(parsed.object.model_dump())
        return parsed
    if name.startswith("transition-"):
        parsed = parse_state_transition(data)
        assert_mandatory_tenant_and_actor(parsed.model_dump(by_alias=True))
        return parsed
    if name.startswith("provider-command-"):
        parsed = parse_provider_command(data)
        assert_mandatory_tenant_and_actor(parsed.model_dump())
        return parsed
    if name.startswith("provider-result-"):
        parsed = parse_provider_result(data)
        assert_mandatory_tenant_and_actor(parsed.model_dump())
        return parsed
    if name.startswith("readiness-"):
        return parse_readiness_report(data)
    raise ValueError(f"Unhandled fixture naming: {name}")


__all__ = [
    "CUSTOMER_CONCIERGE_CONTRACT_VERSION",
    "PROVIDER_NAMES",
    "ValidationError",
    "assert_mandatory_tenant_and_actor",
    "parse_domain_wrapper",
    "parse_event_envelope",
    "parse_provider_command",
    "parse_provider_result",
    "parse_readiness_report",
    "parse_state_transition",
    "validate_fixture_file",
]
