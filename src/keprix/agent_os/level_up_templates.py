"""Map maturity gaps to level-up actions."""

from __future__ import annotations

from itertools import count
from typing import Any

from keprix.agent_os.level_up_store import LevelUpAction


def leverage_label(value: int | float) -> str:
    if value >= 85:
        return "high"
    if value >= 65:
        return "medium"
    return "low"


def action_for_gap(gap: dict[str, Any], seq: int) -> LevelUpAction:
    title = str(gap.get("title") or "Improve OS maturity")
    dimension = str(gap.get("dimension") or "context")
    lower = title.lower()
    if "connections.md" in lower or "connection" in lower:
        return LevelUpAction(
            id=f"act-{seq}",
            title=title,
            dimension="connections",
            leverage=leverage_label(gap.get("leverage") or 70),
            kind="auto_stub" if "connections.md" in lower else "wizard",
            action_url="/agent-os/connections",
            skill_slug="level-up",
            instructions_md="Initialize or update connections.md, then mark one tier-1 domain live after user approval.",
        )
    if "context/" in lower or "writing" in lower or "priorities" in lower:
        return LevelUpAction(
            id=f"act-{seq}",
            title=title,
            dimension="context",
            leverage=leverage_label(gap.get("leverage") or 90),
            kind="auto_stub" if "priorities" in lower else "wizard",
            action_url="/agent-os/onboard",
            skill_slug="onboard",
            instructions_md="Run the onboard interview or create the missing context file with operator-approved content.",
        )
    if "cron" in lower or "cadence" in lower or "ledger" in lower:
        return LevelUpAction(
            id=f"act-{seq}",
            title=title,
            dimension="cadence",
            leverage=leverage_label(gap.get("leverage") or 60),
            kind="wizard",
            action_url="/agent-os/promote",
            skill_slug="level-up",
            instructions_md="Promote a recurring action and schedule a weekly review cadence.",
        )
    return LevelUpAction(
        id=f"act-{seq}",
        title=title,
        dimension=dimension,
        leverage=leverage_label(gap.get("leverage") or 50),
        kind="manual",
        action_url="/hub",
        skill_slug="level-up",
        instructions_md="Review the maturity gap and choose the next safe operator-approved action.",
    )


def actions_from_export(export: dict[str, Any]) -> list[LevelUpAction]:
    seq = count(1)
    actions = [action_for_gap(gap, next(seq)) for gap in export.get("top_gaps") or []]
    actions.sort(key=lambda action: {"high": 0, "medium": 1, "low": 2}.get(action.leverage, 1))
    return actions
