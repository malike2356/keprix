"""Scout signals and guards for Hermes-adopted Keprix features."""

from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import Any

from keprix.security.prompt_guard import analyze_prompt
from keprix.security.rate_limiter import rate_limit
from keprix.security.scout_integration import emit_scout_signal
from keprix.security.scout_types import SignalCategory, SignalSeverity

logger = logging.getLogger(__name__)

_MOA_WINDOW_SECONDS = 10 * 60
_MOA_MAX_CALLS = 5
_X_SEARCH_PER_MINUTE = 10
_X_SEARCH_PER_HOUR = 100


def _preview_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def guard_prompt_text(text: str, *, source: str) -> tuple[bool, str | None]:
    """Return (allowed, error_message). Blocks high-confidence injection attempts."""
    result = analyze_prompt(text)
    if not result.suspicious:
        return True, None
    if result.confidence >= 0.7:
        emit_scout_signal(
            SignalCategory.PROMPT_INJECTION,
            SignalSeverity.CRITICAL,
            f"{source}_injection_blocked",
            f"source:{source}",
            {
                "patterns_matched": result.patterns,
                "confidence": result.confidence,
                "input_hash": _preview_hash(text),
            },
            threat_score=result.confidence,
        )
        return False, f"Prompt injection detected in {source}"
    return True, None


def is_tool_governance_blocked(tool_name: str) -> bool:
    try:
        from keprix.governance.policy_receiver import get_policy_registry

        return get_policy_registry().is_tool_blocked(tool_name)
    except Exception:
        return False


def emit_checkpoint_created(*, working_dir: str, reason: str, commit_hash: str) -> None:
    emit_scout_signal(
        SignalCategory.GOVERNANCE,
        SignalSeverity.INFO,
        "checkpoint.created",
        f"workspace:{working_dir}",
        {
            "reason": reason,
            "git_hash": commit_hash,
            "checkpoint_id": f"ckpt-{commit_hash[:12]}",
        },
    )


def emit_checkpoint_rollback(
    *,
    working_dir: str,
    commit_hash: str,
    success: bool,
    triggered_by: str = "manual",
) -> None:
    action = "checkpoint.auto_rollback" if triggered_by == "governance" else "checkpoint.rollback"
    emit_scout_signal(
        SignalCategory.GOVERNANCE,
        SignalSeverity.WARNING if not success else SignalSeverity.INFO,
        action,
        f"checkpoint:{commit_hash[:12]}",
        {
            "workspace": working_dir,
            "commit_hash": commit_hash,
            "success": success,
            "triggered_by": triggered_by,
        },
    )


def check_moa_rate_limit(identifier: str | None = None) -> bool:
    key = identifier or os.environ.get("KEPRIX_SESSION_ID", "default")
    allowed = rate_limit(
        "moa_synthesis",
        key,
        limit=_MOA_MAX_CALLS,
        window_seconds=_MOA_WINDOW_SECONDS,
    )
    if not allowed:
        emit_scout_signal(
            SignalCategory.RATE_LIMIT,
            SignalSeverity.WARNING,
            "moa_rate_limited",
            f"session:{key}",
            {"window_seconds": _MOA_WINDOW_SECONDS, "limit": _MOA_MAX_CALLS},
        )
    return allowed


def emit_moa_complete(
    *,
    reference_models: list[str],
    aggregator_model: str,
    total_tokens: int,
    duration_seconds: float,
    failed_models: list[str],
) -> None:
    emit_scout_signal(
        SignalCategory.GOVERNANCE,
        SignalSeverity.INFO,
        "moa_synthesis_complete",
        f"moa:{len(reference_models)}_models",
        {
            "reference_models": reference_models,
            "aggregator_model": aggregator_model,
            "total_tokens": total_tokens,
            "duration_seconds": duration_seconds,
            "failed_models": failed_models,
        },
    )


def emit_moa_output_sanitized(alerts: list[str]) -> None:
    if not alerts:
        return
    emit_scout_signal(
        SignalCategory.GOVERNANCE,
        SignalSeverity.WARNING,
        "moa_output_sanitized",
        "moa_aggregator",
        {"alerts": alerts},
    )


def check_x_search_rate_limit(identifier: str | None = None) -> bool:
    key = identifier or os.environ.get("KEPRIX_SESSION_ID", "default")
    minute_ok = rate_limit("x_search_minute", key, limit=_X_SEARCH_PER_MINUTE, window_seconds=60)
    hour_ok = rate_limit("x_search_hour", key, limit=_X_SEARCH_PER_HOUR, window_seconds=3600)
    if not minute_ok or not hour_ok:
        emit_scout_signal(
            SignalCategory.RATE_LIMIT,
            SignalSeverity.WARNING,
            "x_search_rate_limited",
            f"session:{key}",
            {
                "minute_limit": _X_SEARCH_PER_MINUTE,
                "hour_limit": _X_SEARCH_PER_HOUR,
                "minute_ok": minute_ok,
                "hour_ok": hour_ok,
            },
        )
        return False
    return True


def emit_x_search_executed(*, query: str, degraded: bool, citation_count: int) -> None:
    emit_scout_signal(
        SignalCategory.GOVERNANCE,
        SignalSeverity.INFO,
        "x_search_executed",
        "tool:x_search",
        {
            "query_hash": _preview_hash(query),
            "degraded": degraded,
            "citation_count": citation_count,
        },
    )


def emit_bridge_tool_usage(
    bridge_name: str,
    *,
    target: str,
    details: dict[str, Any] | None = None,
) -> None:
    emit_scout_signal(
        SignalCategory.GOVERNANCE,
        SignalSeverity.INFO,
        "bridge_tool_call",
        target,
        {"bridge": bridge_name, **(details or {})},
    )


def scan_output_for_injection(text: str) -> tuple[str, list[str]]:
    """Lightweight output guard using prompt heuristics."""
    result = analyze_prompt(text)
    alerts: list[str] = []
    if result.suspicious:
        alerts.append(
            f"suspicious_output_patterns:{','.join(result.patterns)}"
        )
    return text, alerts
