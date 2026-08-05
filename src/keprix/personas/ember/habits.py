"""Habit tracking and accountability for EMBER."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from keprix.compat import UTC
from typing import Any
from uuid import uuid4

from keprix.personas.ember.coach import WELLBEING_VAULT_CATEGORY, WELLBEING_VAULT_TAG
from keprix.personas.ember.persona import EMBER_PERSONA
from keprix.security.vault_service import get_vault_service
from keprix.workspace.repository import workspace_repo

HABIT_TASK_TAG = "ember-habit"


@dataclass(slots=True)
class HabitRecord:
    habit_id: str
    name: str
    frequency: str
    streak: int
    longest_streak: int
    completion_dates: list[str] = field(default_factory=list)
    task_id: str | None = None
    vault_item_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "habit_id": self.habit_id,
            "name": self.name,
            "frequency": self.frequency,
            "streak": self.streak,
            "longest_streak": self.longest_streak,
            "completion_dates": list(self.completion_dates),
            "task_id": self.task_id,
            "vault_item_id": self.vault_item_id,
        }


@dataclass
class HabitPlan:
    plan_id: str
    habit_name: str
    frequency: str
    motivation: str
    tiny_start: str
    cue: str
    reward: str
    accountability: str
    streak: int
    longest_streak: int
    completion_count: int
    markdown: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "habit_name": self.habit_name,
            "frequency": self.frequency,
            "motivation": self.motivation,
            "tiny_start": self.tiny_start,
            "cue": self.cue,
            "reward": self.reward,
            "accountability": self.accountability,
            "streak": self.streak,
            "longest_streak": self.longest_streak,
            "completion_count": self.completion_count,
            "markdown": self.markdown,
        }


def _compute_streak(completion_dates: list[str], *, today: date | None = None) -> tuple[int, int]:
    if not completion_dates:
        return 0, 0
    day = today or datetime.now(UTC).date()
    unique_days = sorted({date.fromisoformat(value) for value in completion_dates}, reverse=True)
    streak = 0
    cursor = day
    for completed in unique_days:
        if completed == cursor:
            streak += 1
            cursor -= timedelta(days=1)
        elif completed < cursor:
            break
    longest = 0
    run = 0
    prev: date | None = None
    for completed in sorted(unique_days):
        if prev and (completed - prev).days == 1:
            run += 1
        else:
            run = 1
        longest = max(longest, run)
        prev = completed
    return streak, longest


async def _save_habit_record(user_id: str, record: dict[str, Any]) -> str:
    vault = get_vault_service()
    item = await vault.create_item(
        user_id,
        label=f"habit-{record['habit_id']}",
        value=json.dumps(record),
        category=WELLBEING_VAULT_CATEGORY,
        tags=[WELLBEING_VAULT_TAG, HABIT_TASK_TAG],
    )
    return item.id


async def _load_habit_records(user_id: str) -> list[dict[str, Any]]:
    vault = get_vault_service()
    items = await vault.list_items(user_id, category=WELLBEING_VAULT_CATEGORY)
    by_id: dict[str, dict[str, Any]] = {}
    for item in sorted(items, key=lambda row: row.updated_at):
        if HABIT_TASK_TAG not in item.tags:
            continue
        full = await vault.get_item(item.id, user_id, decrypt=True)
        if full and full._value:
            record = json.loads(full._value)
            habit_id = record.get("habit_id")
            if habit_id:
                record["vault_item_id"] = item.id
                by_id[str(habit_id)] = record
    return list(by_id.values())


class EmberHabits:
    def __init__(self, *, workspace_id: str = "default", user_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.persona = EMBER_PERSONA
        self._user = {"id": user_id, "username": user_id}
        self._plan_template = self.persona.prompts_dir / "habit_plan.md"

    async def create_habit(
        self,
        *,
        name: str,
        frequency: str = "daily",
        motivation: str = "",
        tiny_start: str = "",
        cue: str = "",
        reward: str = "",
    ) -> HabitRecord:
        habit_id = str(uuid4())
        task = workspace_repo.create_task(
            self._user,
            title=f"Habit: {name}",
            description=f"Wellbeing lane habit ({frequency})",
            tags=[HABIT_TASK_TAG, "wellbeing-lane"],
            agent_scheduled=False,
        )
        record = {
            "habit_id": habit_id,
            "name": name,
            "frequency": frequency,
            "motivation": motivation,
            "tiny_start": tiny_start or f"Two minutes of {name.lower()}",
            "cue": cue or "After morning coffee",
            "reward": reward or "Mark it done and notice how you feel",
            "completion_dates": [],
            "streak": 0,
            "longest_streak": 0,
            "task_id": task["id"],
        }
        vault_item_id = await _save_habit_record(self.user_id, record)
        return HabitRecord(
            habit_id=habit_id,
            name=name,
            frequency=frequency,
            streak=0,
            longest_streak=0,
            task_id=task["id"],
            vault_item_id=vault_item_id,
        )

    async def log_completion(self, habit_id: str, *, on_date: date | None = None) -> HabitRecord:
        records = await _load_habit_records(self.user_id)
        match = next((row for row in records if row.get("habit_id") == habit_id), None)
        if match is None:
            raise KeyError(habit_id)

        day = (on_date or datetime.now(UTC).date()).isoformat()
        dates = list(match.get("completion_dates", []))
        if day not in dates:
            dates.append(day)
        streak, longest = _compute_streak(dates)
        match["completion_dates"] = dates
        match["streak"] = streak
        match["longest_streak"] = max(longest, int(match.get("longest_streak", 0)))

        vault_item_id = await _save_habit_record(self.user_id, match)
        task_id = match.get("task_id")
        if task_id:
            workspace_repo.complete_task(self._user, task_id)

        return HabitRecord(
            habit_id=habit_id,
            name=match["name"],
            frequency=match.get("frequency", "daily"),
            streak=streak,
            longest_streak=match["longest_streak"],
            completion_dates=dates,
            task_id=task_id,
            vault_item_id=vault_item_id,
        )

    async def list_habits(self) -> list[HabitRecord]:
        records = await _load_habit_records(self.user_id)
        rows: list[HabitRecord] = []
        for match in records:
            dates = list(match.get("completion_dates", []))
            streak, longest = _compute_streak(dates)
            rows.append(
                HabitRecord(
                    habit_id=match["habit_id"],
                    name=match["name"],
                    frequency=match.get("frequency", "daily"),
                    streak=streak,
                    longest_streak=max(longest, int(match.get("longest_streak", 0))),
                    completion_dates=dates,
                    task_id=match.get("task_id"),
                )
            )
        return rows

    def render_plan(self, record: dict[str, Any]) -> str:
        template = self._plan_template.read_text(encoding="utf-8")
        dates = record.get("completion_dates", [])
        streak, longest = _compute_streak(dates)
        return (
            template.replace("{{habit_name}}", record.get("name", "Habit"))
            .replace("{{plan_id}}", record.get("habit_id", ""))
            .replace("{{frequency}}", record.get("frequency", "daily"))
            .replace("{{motivation}}", record.get("motivation", "Small steps compound."))
            .replace("{{tiny_start}}", record.get("tiny_start", ""))
            .replace("{{cue}}", record.get("cue", ""))
            .replace("{{reward}}", record.get("reward", ""))
            .replace("{{accountability}}", "Track streak privately in the wellbeing lane.")
            .replace("{{streak}}", str(streak))
            .replace("{{longest_streak}}", str(longest))
            .replace("{{completion_count}}", str(len(dates)))
            .replace("{{next_checkin}}", "Tomorrow, same cue.")
        )

    async def build_plan(self, habit_id: str) -> HabitPlan:
        records = await _load_habit_records(self.user_id)
        match = next((row for row in records if row.get("habit_id") == habit_id), None)
        if match is None:
            raise KeyError(habit_id)
        dates = list(match.get("completion_dates", []))
        streak, longest = _compute_streak(dates)
        markdown = self.render_plan(match)
        return HabitPlan(
            plan_id=habit_id,
            habit_name=match["name"],
            frequency=match.get("frequency", "daily"),
            motivation=match.get("motivation", ""),
            tiny_start=match.get("tiny_start", ""),
            cue=match.get("cue", ""),
            reward=match.get("reward", ""),
            accountability="Private wellbeing lane tracking",
            streak=streak,
            longest_streak=longest,
            completion_count=len(dates),
            markdown=markdown,
        )
