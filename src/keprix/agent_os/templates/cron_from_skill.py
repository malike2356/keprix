"""Cron promotion template."""

from __future__ import annotations

from typing import Any


def cron_spec(skill_slug: str, *, name: str | None = None, schedule: str = "0 8 * * 1-5", deliver_to: str = "local") -> dict[str, Any]:
    return {
        "name": name or skill_slug,
        "schedule": schedule,
        "prompt": f"/{skill_slug}",
        "skills": [skill_slug],
        "deliver_to": deliver_to,
    }
