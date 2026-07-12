"""Interactive day 1 / day 7 / day 30 milestone wizard (Prompt 270 Task 4.5)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from keprix.agent_os.onboarding_progress import OnboardingProgressStore
from keprix.agent_os.onboarding_steps import STEPS


@dataclass(frozen=True)
class MilestoneDef:
    id: str
    day: int
    title: str
    step_ids: tuple[str, ...]
    copy: str


MILESTONES: tuple[MilestoneDef, ...] = (
    MilestoneDef(
        id="day_1",
        day=1,
        title="Day 1: First result",
        step_ids=("a1_provider", "a2_first_chat", "a2b_hello_world", "a3b_vault"),
        copy="Install, connect a provider, run Hello World, confirm the single vault.",
    ),
    MilestoneDef(
        id="day_7",
        day=7,
        title="Day 7: Memory + three workflows",
        step_ids=("l0_onboard", "l1_audit", "l1_first_skill", "l2_four_cs_audit"),
        copy="Vault notes flowing, audit done, first skill approved, maturity pulse.",
    ),
    MilestoneDef(
        id="day_30",
        day=30,
        title="Day 30: Full Agent OS",
        step_ids=("l3_pin", "l3_headless", "l3_schedule", "l4_kit"),
        copy="Glass dashboard habit, headless runs, schedules, client kit or teammate invite.",
    ),
)


def _step_labels() -> dict[str, str]:
    return {step.id: step.title for step in STEPS}


def build_milestones(*, user_id: str = "default") -> dict[str, Any]:
    progress = OnboardingProgressStore().load(user_id)
    steps = progress.steps
    labels = _step_labels()
    milestones: list[dict[str, Any]] = []
    for item in MILESTONES:
        existing = [sid for sid in item.step_ids if sid in labels]
        done = sum(1 for sid in existing if steps.get(sid))
        total = len(existing) or 1
        complete = done == total and total > 0
        milestones.append(
            {
                "id": item.id,
                "day": item.day,
                "title": item.title,
                "copy": item.copy,
                "done": done,
                "total": total,
                "percent": round(100 * done / total),
                "complete": complete,
                "steps": [
                    {
                        "id": sid,
                        "title": labels.get(sid, sid),
                        "complete": bool(steps.get(sid)),
                    }
                    for sid in existing
                ],
            }
        )

    current = next((row for row in milestones if not row["complete"]), milestones[-1] if milestones else None)
    return {
        "ok": True,
        "user_id": user_id,
        "milestones": milestones,
        "current": current,
        "all_complete": all(row["complete"] for row in milestones) if milestones else False,
        "links": {
            "onboarding": "/agent-os/onboarding",
            "glass": "/agent-os/glass",
            "hello": "/agent-apps",
        },
    }
