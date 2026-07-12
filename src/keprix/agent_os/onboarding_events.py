"""Event hooks for Agent OS onboarding progress."""

from __future__ import annotations

from typing import Any

from keprix.agent_os.onboarding_progress import OnboardingProgress, OnboardingProgressStore
from keprix.agent_os.onboarding_steps import EVENT_TO_STEP_IDS


def user_id_from_user(user: dict[str, Any] | None) -> str:
    user = user or {}
    return str(user.get("id") or user.get("user_id") or user.get("username") or "default")


def record_onboarding_event(user_id: str, event_name: str) -> OnboardingProgress:
    step_ids = EVENT_TO_STEP_IDS.get(event_name, ())
    store = OnboardingProgressStore()
    progress = store.load(user_id)
    for step_id in step_ids:
        progress.steps[step_id] = True
    return store.save(progress)


def record_onboarding_event_for_user(user: dict[str, Any] | None, event_name: str) -> OnboardingProgress:
    return record_onboarding_event(user_id_from_user(user), event_name)
