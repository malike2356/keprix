"""Scheduled wellbeing check-ins for EMBER."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from keprix.cron.jobs import create_job, load_jobs
from keprix.personas.ember.coach import PROFESSIONAL_HELP_NOTE, WELLBEING_VAULT_CATEGORY, WELLBEING_VAULT_TAG
from keprix.personas.ember.persona import EMBER_PERSONA
from keprix.security.vault_service import get_vault_service

CHECKIN_DIMENSIONS = ("energy", "stress", "focus", "sleep", "mood")
NEGATIVE_MOOD_THRESHOLD = 2
HIGH_STRESS_THRESHOLD = 4
LOW_ENERGY_THRESHOLD = 2

SCHEDULE_PRESETS: dict[str, str] = {
    "daily": "0 9 * * *",
    "weekdays": "0 9 * * 1-5",
    "weekly": "0 9 * * 1",
}


@dataclass(slots=True)
class CheckinRecord:
    checkin_id: str
    submitted_at: str
    energy: int
    stress: int
    focus: int
    sleep: int
    mood: int
    notes: str = ""
    reflection: str = ""
    suggestion: str = ""
    pattern_note: str = ""
    vault_item_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkin_id": self.checkin_id,
            "submitted_at": self.submitted_at,
            "energy": self.energy,
            "stress": self.stress,
            "focus": self.focus,
            "sleep": self.sleep,
            "mood": self.mood,
            "notes": self.notes,
            "reflection": self.reflection,
            "suggestion": self.suggestion,
            "pattern_note": self.pattern_note,
            "vault_item_id": self.vault_item_id,
        }


@dataclass
class CheckinSchedule:
    job_id: str
    user_id: str
    frequency: str
    schedule: str
    topics: list[str]
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "user_id": self.user_id,
            "frequency": self.frequency,
            "schedule": self.schedule,
            "topics": list(self.topics),
            "enabled": self.enabled,
        }


def _clamp_score(value: int) -> int:
    return max(1, min(5, int(value)))


def count_negative_checkin_streak(records: list[dict[str, Any]]) -> int:
    streak = 0
    for row in reversed(records):
        energy = int(row.get("energy", 3))
        mood = int(row.get("mood", 3))
        stress = int(row.get("stress", 3))
        if energy <= NEGATIVE_MOOD_THRESHOLD or mood <= NEGATIVE_MOOD_THRESHOLD or stress >= HIGH_STRESS_THRESHOLD:
            streak += 1
        else:
            break
    return streak


def detect_burnout_signals(records: list[dict[str, Any]], *, missed_days: int = 0) -> list[str]:
    signals: list[str] = []
    if len(records) < 2 and missed_days == 0:
        return signals

    recent = records[-3:] if records else []
    if recent:
        avg_energy = sum(int(row.get("energy", 3)) for row in recent) / len(recent)
        avg_stress = sum(int(row.get("stress", 3)) for row in recent) / len(recent)
        if avg_energy <= LOW_ENERGY_THRESHOLD:
            signals.append("declining_energy")
        if avg_stress >= HIGH_STRESS_THRESHOLD:
            signals.append("increasing_stress")
        low_mood = sum(1 for row in recent if int(row.get("mood", 3)) <= NEGATIVE_MOOD_THRESHOLD)
        if low_mood >= 2:
            signals.append("persistent_low_mood")

    if missed_days >= 3:
        signals.append("skipped_checkins")

    return signals


async def _store_checkin(user_id: str, record: dict[str, Any]) -> str:
    vault = get_vault_service()
    item = await vault.create_item(
        user_id,
        label=f"checkin-{record['checkin_id']}",
        value=json.dumps(record),
        category=WELLBEING_VAULT_CATEGORY,
        tags=[WELLBEING_VAULT_TAG, "ember-checkin"],
    )
    return item.id


async def _load_checkins(user_id: str) -> list[dict[str, Any]]:
    vault = get_vault_service()
    items = await vault.list_items(user_id, category=WELLBEING_VAULT_CATEGORY)
    records: list[dict[str, Any]] = []
    for item in items:
        if "ember-checkin" not in item.tags:
            continue
        full = await vault.get_item(item.id, user_id, decrypt=True)
        if full and full._value:
            records.append(json.loads(full._value))
    records.sort(key=lambda row: row.get("submitted_at", ""))
    return records


class EmberCheckin:
    def __init__(self, *, user_id: str = "default") -> None:
        self.user_id = user_id
        self.persona = EMBER_PERSONA
        self._template = self.persona.prompts_dir / "checkin.md"

    def build_prompt_topics(self, topics: list[str] | None = None) -> list[str]:
        selected = topics or list(CHECKIN_DIMENSIONS)
        return [topic for topic in selected if topic in CHECKIN_DIMENSIONS] or list(CHECKIN_DIMENSIONS)

    def render_checkin_markdown(self, record: CheckinRecord) -> str:
        template = self._template.read_text(encoding="utf-8")
        return (
            template.replace("{{date}}", record.submitted_at[:10])
            .replace("{{checkin_id}}", record.checkin_id)
            .replace("{{energy}}", str(record.energy))
            .replace("{{stress}}", str(record.stress))
            .replace("{{focus}}", str(record.focus))
            .replace("{{sleep}}", str(record.sleep))
            .replace("{{mood}}", str(record.mood))
            .replace("{{energy_note}}", record.notes if record.energy <= 2 else "")
            .replace("{{stress_note}}", record.notes if record.stress >= 4 else "")
            .replace("{{focus_note}}", "")
            .replace("{{sleep_note}}", record.notes if record.sleep <= 2 else "")
            .replace("{{mood_note}}", record.notes if record.mood <= 2 else "")
            .replace("{{reflection}}", record.reflection)
            .replace("{{suggestion}}", record.suggestion)
            .replace("{{pattern_note}}", record.pattern_note)
        )

    async def submit_checkin(
        self,
        *,
        energy: int,
        stress: int,
        focus: int,
        sleep: int,
        mood: int,
        notes: str = "",
    ) -> CheckinRecord:
        submitted_at = datetime.now(UTC).isoformat()
        history = await _load_checkins(self.user_id)
        negative_streak = count_negative_checkin_streak(history)

        reflection = "You checked in today; that counts."
        if energy <= 2:
            reflection = "Energy looks low. Be gentle with your schedule today."
        elif stress >= 4:
            reflection = "Stress is running high. A short pause could help."

        suggestion = "Pick one small recovery action: a walk, water, or five quiet minutes."
        pattern_note = "Patterns will become clearer after a few check-ins."
        if negative_streak >= 2:
            pattern_note = "Energy, mood, or stress has been difficult across recent check-ins."
            suggestion = PROFESSIONAL_HELP_NOTE

        burnout = detect_burnout_signals(history)
        if burnout:
            pattern_note = f"Burnout signals noticed: {', '.join(burnout)}. Consider boundaries and rest."

        record = CheckinRecord(
            checkin_id=str(uuid4()),
            submitted_at=submitted_at,
            energy=_clamp_score(energy),
            stress=_clamp_score(stress),
            focus=_clamp_score(focus),
            sleep=_clamp_score(sleep),
            mood=_clamp_score(mood),
            notes=notes.strip(),
            reflection=reflection,
            suggestion=suggestion,
            pattern_note=pattern_note,
        )
        payload = record.to_dict()
        payload["markdown"] = self.render_checkin_markdown(record)
        record.vault_item_id = await _store_checkin(self.user_id, payload)
        return record

    async def list_checkins(self, *, limit: int = 30) -> list[CheckinRecord]:
        rows = await _load_checkins(self.user_id)
        records: list[CheckinRecord] = []
        for row in rows[-limit:]:
            records.append(
                CheckinRecord(
                    checkin_id=row["checkin_id"],
                    submitted_at=row["submitted_at"],
                    energy=int(row["energy"]),
                    stress=int(row["stress"]),
                    focus=int(row["focus"]),
                    sleep=int(row["sleep"]),
                    mood=int(row["mood"]),
                    notes=row.get("notes", ""),
                    reflection=row.get("reflection", ""),
                    suggestion=row.get("suggestion", ""),
                    pattern_note=row.get("pattern_note", ""),
                    vault_item_id=row.get("vault_item_id"),
                )
            )
        return records

    async def run_scheduled_checkin(self) -> CheckinRecord:
        """Execute a cron-fired wellbeing check-in."""
        return await self.submit_checkin(
            energy=3,
            stress=3,
            focus=3,
            sleep=3,
            mood=3,
            notes="Scheduled wellbeing check-in",
        )

    def schedule_checkins(
        self,
        *,
        frequency: str = "daily",
        topics: list[str] | None = None,
    ) -> CheckinSchedule:
        cron_expr = SCHEDULE_PRESETS.get(frequency, SCHEDULE_PRESETS["daily"])
        topic_list = self.build_prompt_topics(topics)
        prompt = (
            f"EMBER wellbeing check-in for user {self.user_id}. "
            f"Topics: {', '.join(topic_list)}. Wellbeing lane only; do not include work output."
        )
        job = create_job(
            prompt=prompt,
            schedule=cron_expr,
            name=f"ember-checkin-{self.user_id}",
            skill="wellbeing-checkin",
            deliver="local",
        )
        return CheckinSchedule(
            job_id=str(job.get("id", "")),
            user_id=self.user_id,
            frequency=frequency,
            schedule=cron_expr,
            topics=topic_list,
            enabled=bool(job.get("enabled", True)),
        )

    def list_schedules(self) -> list[CheckinSchedule]:
        prefix = f"ember-checkin-{self.user_id}"
        rows: list[CheckinSchedule] = []
        for job in load_jobs():
            if job.get("name") == prefix:
                rows.append(
                    CheckinSchedule(
                        job_id=str(job.get("id", "")),
                        user_id=self.user_id,
                        frequency="custom",
                        schedule=str(job.get("schedule", "")),
                        topics=list(CHECKIN_DIMENSIONS),
                        enabled=bool(job.get("enabled", True)),
                    )
                )
        return rows

    def days_since_last_checkin(self, records: list[dict[str, Any]]) -> int:
        if not records:
            return 999
        last = records[-1].get("submitted_at", "")
        try:
            last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        except ValueError:
            return 0
        delta = datetime.now(UTC) - last_dt
        return max(0, delta.days)

    async def burnout_assessment(self) -> dict[str, Any]:
        records = await _load_checkins(self.user_id)
        missed = self.days_since_last_checkin(records)
        signals = detect_burnout_signals(records, missed_days=missed)
        return {
            "signals": signals,
            "negative_checkin_streak": count_negative_checkin_streak(records),
            "days_since_last_checkin": missed,
            "suggest_professional_help": count_negative_checkin_streak(records) >= 3,
            "boundary_suggestions": [
                "Block a 15-minute recovery break on your calendar",
                "End work at a fixed time twice this week",
                "Say no to one non-essential commitment",
            ]
            if signals
            else [],
        }
