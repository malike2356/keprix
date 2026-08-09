"""Generated Propreneur result envelope constants (prompt 637). Do not hand-edit."""
from __future__ import annotations

from typing import Any, Literal, TypedDict

ENVELOPE_SCHEMA = '"propreneur_result_envelope.v1"'
ENVELOPE_VERSION = '"1.0.0"'

ExecutionStatus = Literal[
    'planned',
    'awaiting_approval',
    'accepted',
    'completed',
    'partially_completed',
    'failed',
    'not_configured',
]

class PropreneurResultEnvelope(TypedDict, total=False):
    success: bool
    data: Any
    error: dict[str, Any] | None
    status: ExecutionStatus
    correlation_id: str
    idempotency: dict[str, Any] | None
    approval: dict[str, Any] | None
    audit_reference: str | None
    retry: dict[str, Any] | None
