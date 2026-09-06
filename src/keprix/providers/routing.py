"""Cost-based model routing escalation (prompt 10).

Automatic model escalation driven by cost/privacy policy. Default OFF; when the
per-workspace routing config is absent or disabled, route_model returns the cheap
model unchanged, so behaviour is byte-identical to today.

Design rules:
- Complexity scoring is a deterministic heuristic on the incoming turn; it never
  reads or mutates the cached system prompt or message history.
- Cost figures come from billing/wallet/pricing.py (pricing_for/raw_cost_usd),
  never hardcoded.
- A rolling-hour per-workspace budget is enforced; when exhausted the cheap model
  is returned instead of erroring.
- Every decision writes a cheap, non-blocking, tenant-scoped audit event to a
  durable JSONL under KEPRIX_HOME. Estimated cost is advisory only; actual
  provider usage remains the billing source of truth.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from keprix_constants import get_keprix_home

# ---------------------------------------------------------------------------
# Configuration (default off). A workspace entry maps to these fields.
# ---------------------------------------------------------------------------


@dataclass
class RoutingConfig:
    enabled: bool = False
    cheap_model: str = ""  # the model to use below threshold / when budget exhausted
    strong_model: str = ""  # escalation target
    strong_provider: str = ""  # provider for the strong model
    complexity_threshold: int = 60  # 0-100
    hourly_budget_credits: int = 0  # rolling-hour budget; 0 = unlimited


_ROUTING_CONFIGS: dict[str, RoutingConfig] = {}


def configure_routing(workspace_id: str, config: RoutingConfig) -> None:
    _ROUTING_CONFIGS[workspace_id] = config


def routing_config(workspace_id: str) -> RoutingConfig:
    return _ROUTING_CONFIGS.get(workspace_id, RoutingConfig())


# ---------------------------------------------------------------------------
# Complexity heuristic (deterministic; no history mutation)
# ---------------------------------------------------------------------------

_HARD_SIGNALS = (
    r"\brefactor\b",
    r"\bdebug\b",
    r"\bsecurity\b",
    r"\bmigrat\w+\b",
    r"\broot cause\b",
    r"\breview\b",
    r"\bdesign\b",
    r"\barchitecture\b",
    r"\bimplement\b",
    r"\bbuild\b",
    r"\boptimiz\w+\b",
    r"\bmultistep\b|\bmulti-step\b",
    r"\bcomprehens\w+\b|\bthorough\b|\bdeep\b",
)
_SIMPLE_SIGNALS = (
    r"\bhi\b",
    r"\bhello\b",
    r"\bthanks\b",
    r"\bok\b",
    r"\byes\b",
    r"\bno\b",
    r"\bwhat is\b",
    r"\bsummarize\b",
)


def complexity_score(text: str, *, history_len: int = 0) -> int:
    """Deterministic 0-100 complexity score for an incoming turn."""
    t = (text or "").lower()
    score = 0
    for pattern in _HARD_SIGNALS:
        if re.search(pattern, t):
            score += 12
    for pattern in _SIMPLE_SIGNALS:
        if re.search(pattern, t):
            score -= 8
    score += min(20, history_len // 4)  # longer contexts are slightly harder
    score += min(10, len(t) // 500)
    return max(0, min(100, score))


# ---------------------------------------------------------------------------
# Rolling-hour budget
# ---------------------------------------------------------------------------


@dataclass
class _Window:
    start: float = field(default_factory=time.monotonic)
    credits: int = 0


_budgets: dict[str, _Window] = {}


def _rolling_spend(workspace_id: str) -> int:
    win = _budgets.get(workspace_id)
    if win is None or (time.monotonic() - win.start) > 3600:
        return 0
    return win.credits


def _record_spend(workspace_id: str, credits: int) -> None:
    win = _budgets.get(workspace_id)
    if win is None or (time.monotonic() - win.start) > 3600:
        win = _Window()
        _budgets[workspace_id] = win
    win.credits += max(0, int(credits))


def reset_routing_budget(workspace_id: str) -> None:
    _budgets.pop(workspace_id, None)


# ---------------------------------------------------------------------------
# Audit (cheap, non-blocking, durable JSONL)
# ---------------------------------------------------------------------------


def _audit_path() -> Path:
    p = get_keprix_home() / "routing" / "routing-audit.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _emit_audit(record: dict[str, Any]) -> None:
    try:
        with _audit_path().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str) + "\n")
    except Exception:  # noqa: BLE001 - audit must never block the turn
        pass


# ---------------------------------------------------------------------------
# Routing decision
# ---------------------------------------------------------------------------


@dataclass
class RoutingDecision:
    model: str
    provider: str = ""
    escalated: bool = False
    reason: str = ""
    estimated_credits: int = 0
    policy_version: str = "routing-v1"


def _estimate_credits(model: str, estimated_tokens: int) -> int:
    try:
        from keprix.billing.wallet.pricing import estimate_credits_for_tokens

        return estimate_credits_for_tokens(model, estimated_tokens)
    except Exception:  # noqa: BLE001
        return 0


def route_model(
    workspace_id: str,
    cheap_model: str,
    cheap_provider: str,
    *,
    turn_text: str,
    history_len: int = 0,
    estimated_tokens: int = 0,
    config: RoutingConfig | None = None,
) -> RoutingDecision:
    """Choose cheap vs strong model for a turn. Default: cheap (byte-identical)."""
    cfg = config or routing_config(workspace_id)

    if not cfg.enabled or not cfg.strong_model:
        decision = RoutingDecision(
            model=cheap_model, provider=cheap_provider, reason="routing_disabled"
        )
        _emit_audit(
            {
                "workspace_id": workspace_id,
                "ts": time.time(),
                "model": cheap_model,
                "escalated": False,
                "reason": decision.reason,
                "policy_version": decision.policy_version,
            }
        )
        return decision

    score = complexity_score(turn_text, history_len=history_len)

    if score < cfg.complexity_threshold:
        decision = RoutingDecision(
            model=cheap_model,
            provider=cheap_provider,
            reason="below_threshold",
            estimated_credits=_estimate_credits(cheap_model, estimated_tokens),
        )
    else:
        est = _estimate_credits(cfg.strong_model, estimated_tokens)
        budget = cfg.hourly_budget_credits
        spent = _rolling_spend(workspace_id)
        if budget > 0 and spent + est > budget:
            decision = RoutingDecision(
                model=cheap_model,
                provider=cheap_provider,
                reason="budget_exhausted",
                estimated_credits=_estimate_credits(cheap_model, estimated_tokens),
            )
        else:
            _record_spend(workspace_id, est)
            decision = RoutingDecision(
                model=cfg.strong_model,
                provider=cfg.strong_provider,
                escalated=True,
                reason=f"escalated_score_{score}",
                estimated_credits=est,
            )

    _emit_audit(
        {
            "workspace_id": workspace_id,
            "ts": time.time(),
            "complexity": score,
            "model": decision.model,
            "escalated": decision.escalated,
            "reason": decision.reason,
            "estimated_credits": decision.estimated_credits,
            "policy_version": decision.policy_version,
        }
    )
    return decision
