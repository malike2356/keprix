"""Helpers for emitting Scout signals from defense layers."""

from __future__ import annotations

import hashlib
from typing import Any

from keprix.security.scout_client import get_scout_client
from keprix.security.scout_types import SignalCategory, SignalSeverity


def _preview_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def emit_scout_signal(
    category: SignalCategory,
    severity: SignalSeverity,
    action: str,
    target: str,
    details: dict[str, Any] | None = None,
    *,
    correlation_id: str | None = None,
    threat_score: float | None = None,
    product_id: str | None = None,
) -> None:
    """Fire-and-forget Scout signal emission. Never raises."""
    try:
        product = product_id
        if not product:
            try:
                from keprix.security.product_context import get_product_context_or_none

                ctx = get_product_context_or_none()
                if ctx is not None:
                    product = ctx.product_id
            except Exception:
                product = "keprix"
        product = product or "keprix"
        get_scout_client().send(
            category,
            severity,
            action,
            target,
            details,
            correlation_id=correlation_id,
            threat_score=threat_score,
        )
        from keprix.security.scout_metrics import record_signal

        record_signal(product, severity=severity.value, action=action)
        from keprix.security.scout_correlation import append_signal_event

        append_signal_event(
            {
                "product": product,
                "category": category.value,
                "severity": severity.value,
                "action": action,
                "target": target,
                "threat_score": threat_score,
                "details": details or {},
            }
        )
        from keprix.security.auto_response import evaluate_signal

        session_id = None
        if details:
            session_id = details.get("session_id")
        evaluate_signal(
            session_id=str(session_id) if session_id else None,
            product_id=product,
            severity=severity.value,
            action=action,
        )
    except Exception:
        pass


def emit_prompt_injection_signal(
    *,
    patterns: list[str],
    source: str,
    text: str,
    confidence: float,
) -> None:
    severity = SignalSeverity.CRITICAL if confidence >= 0.7 else SignalSeverity.WARNING
    emit_scout_signal(
        SignalCategory.PROMPT_INJECTION,
        severity,
        "injection_detected",
        f"source:{source}",
        {
            "patterns_matched": patterns,
            "input_hash": _preview_hash(text),
            "input_preview": text[:200],
            "confidence": confidence,
        },
        threat_score=confidence,
    )


def emit_egress_blocked_signal(
    *,
    product_id: str,
    host: str,
    ip: str,
    reason: str,
) -> None:
    emit_scout_signal(
        SignalCategory.EGRESS_VIOLATION,
        SignalSeverity.WARNING,
        "egress_blocked",
        f"host:{host}",
        {
            "product_id": product_id,
            "ip": ip,
            "reason": reason,
        },
    )


def emit_tool_acl_signal(
    *,
    product_id: str,
    tool_name: str,
    decision: str,
    workspace_id: str | None = None,
) -> None:
    if decision == "allowed":
        return
    emit_scout_signal(
        SignalCategory.TOOL_ABUSE,
        SignalSeverity.WARNING,
        "tool_acl_denied",
        f"tool:{tool_name}",
        {
            "product_id": product_id,
            "decision": decision,
            "workspace_id": workspace_id,
        },
    )
