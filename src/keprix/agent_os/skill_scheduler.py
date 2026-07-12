"""Schedule shortcuts for skill-backed Action Board pins."""

from __future__ import annotations

from typing import Any

from keprix.agent_os.automation_promoter import AutomationPromoter


class SkillScheduler:
    def schedule_skill(self, skill_slug: str, *, schedule: str, name: str | None = None, deliver_to: str = "local") -> dict[str, Any]:
        return AutomationPromoter().promote(
            skill_slug=skill_slug,
            target="cron",
            schedule=schedule,
            name=name,
            deliver_to=deliver_to,
        )
