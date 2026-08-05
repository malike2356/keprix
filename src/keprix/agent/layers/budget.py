"""Budget layer: token budget and resource constraints."""

from __future__ import annotations

from typing import Any

BUDGET_TEMPLATE = """\
Token budget for this session: {budget:,} tokens.
Current usage: {used:,} tokens ({percent}%).
Estimated remaining turns at current rate: {remaining_turns}.

If you approach 80% of your budget:
- Prioritise completion over perfection.
- Prefer one-line answers over paragraphs.
- Skip optional context and tool calls.
- Defer non-critical research to a follow-up session.

If you exceed 95% of your budget:
- Stop execution immediately.
- Summarise what was completed and what remains.
- Suggest how to continue in a new session."""

_DEFAULT_BUDGET = 200_000
_DEFAULT_TOKENS_PER_TURN = 2_000


def _resolve_budget(agent: Any) -> int:
    compressor = getattr(agent, "context_compressor", None)
    if compressor is not None:
        ctx_len = getattr(compressor, "context_length", 0) or 0
        if ctx_len > 0:
            return int(ctx_len)
    config_ctx = getattr(agent, "_config_context_length", None)
    if config_ctx:
        try:
            return int(config_ctx)
        except (TypeError, ValueError):
            pass
    return _DEFAULT_BUDGET


def _estimate_remaining_turns(agent: Any, budget: int, used: int) -> int:
    remaining_tokens = max(budget - used, 0)
    turn_count = int(getattr(agent, "_user_turn_count", 0) or 0)
    if turn_count > 0 and used > 0:
        tokens_per_turn = max(used // turn_count, 1)
    else:
        tokens_per_turn = _DEFAULT_TOKENS_PER_TURN
    return max(remaining_tokens // tokens_per_turn, 0)


def render_budget_layer(agent: Any) -> str:
    budget = _resolve_budget(agent)
    used = int(getattr(agent, "session_total_tokens", 0) or 0)
    percent = int((used / budget) * 100) if budget > 0 else 0
    remaining_turns = _estimate_remaining_turns(agent, budget, used)
    return BUDGET_TEMPLATE.format(
        budget=budget,
        used=used,
        percent=percent,
        remaining_turns=remaining_turns,
    )
