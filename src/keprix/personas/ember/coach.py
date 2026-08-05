"""Coaching conversations and wellbeing lane boundaries for EMBER."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from keprix.compat import UTC
from typing import Any
from uuid import uuid4

from keprix.personas.ember.persona import EMBER_PERSONA
from keprix.security.vault_service import get_vault_service

WELLBEING_LANE = "wellbeing"
WELLBEING_LANE_AGENTS = frozenset({"EMBER"})
WELLBEING_LANE_TAGS = frozenset({"wellbeing-lane", "ember-habit", "ember-checkin", "ember-coaching"})
WELLBEING_VAULT_CATEGORY = "wellbeing"
WELLBEING_VAULT_TAG = "ember-wellbeing-lane"

CRISIS_PATTERNS = (
    r"\b(kill myself|killing myself|end my life|suicide|suicidal)\b",
    r"\b(self[- ]harm|hurt myself|cutting myself)\b",
    r"\b(want to die|wish i was dead|wish i were dead)\b",
    r"\b(harm (someone|others|them)|hurt (someone|others|them))\b",
    r"\b(no reason to live|better off dead)\b",
)

CRISIS_RESOURCES = (
    "Samaritans (UK): call 116 123 (free, 24/7)",
    "Crisis Text Line (UK): text SHOUT to 85258",
    "If you or someone else is in immediate danger, call 999 (UK) or your local emergency number",
    "For urgent mental health advice in the UK: call 111 or visit 111.nhs.uk",
)

PROFESSIONAL_HELP_NOTE = (
    "I have noticed difficult patterns over several check-ins. "
    "Speaking with a qualified counsellor or your GP could help; you do not have to carry this alone."
)

COACHING_PHASES = ("ask", "listen", "reflect", "suggest")


@dataclass(slots=True)
class CrisisResponse:
    detected: bool
    resources: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "detected": self.detected,
            "resources": list(self.resources),
            "message": self.message,
        }


@dataclass
class CoachingResponse:
    session_id: str
    lane: str
    ask: list[str]
    listen: str
    reflect: str
    suggest: list[str]
    crisis: CrisisResponse
    suggest_professional_help: bool = False
    vault_item_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "lane": self.lane,
            "phases": {
                "ask": list(self.ask),
                "listen": self.listen,
                "reflect": self.reflect,
                "suggest": list(self.suggest),
            },
            "crisis": self.crisis.to_dict(),
            "suggest_professional_help": self.suggest_professional_help,
            "vault_item_id": self.vault_item_id,
        }


def is_wellbeing_lane_owner(owner: str) -> bool:
    return owner.strip().upper() in WELLBEING_LANE_AGENTS


def is_wellbeing_lane_tag(tag: str) -> bool:
    return tag in WELLBEING_LANE_TAGS


def detect_crisis_language(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in CRISIS_PATTERNS)


def build_crisis_response() -> CrisisResponse:
    return CrisisResponse(
        detected=True,
        resources=list(CRISIS_RESOURCES),
        message=(
            "I hear that you are going through something really painful. "
            "You deserve support from someone trained to help right now. "
            "Please reach out to one of these services:"
        ),
    )


def detect_limiting_belief(text: str) -> str | None:
    patterns = (
        (r"\bi always fail\b", "Always language can hide exceptions you have already made."),
        (r"\bi never\b", "Never is a strong word; a small counter-example might exist."),
        (r"\bi'm not good enough\b", "Not good enough for whom, and by what measure?"),
        (r"\bi can't\b", "What part feels impossible: skill, energy, or permission?"),
    )
    lowered = text.lower()
    for pattern, reframe in patterns:
        if re.search(pattern, lowered):
            return reframe
    return None


async def store_coaching_turn(user_id: str, payload: dict[str, Any]) -> str:
    vault = get_vault_service()
    item = await vault.create_item(
        user_id,
        label=f"coaching-{payload.get('session_id', uuid4())}",
        value=json.dumps(payload),
        category=WELLBEING_VAULT_CATEGORY,
        tags=[WELLBEING_VAULT_TAG, "ember-coaching"],
    )
    return item.id


class EmberCoach:
    def __init__(self, *, user_id: str = "default") -> None:
        self.user_id = user_id
        self.persona = EMBER_PERSONA

    def coach(
        self,
        message: str,
        *,
        session_id: str | None = None,
        context: str = "",
        negative_checkin_streak: int = 0,
        store: bool = True,
    ) -> CoachingResponse:
        session = session_id or str(uuid4())

        if detect_crisis_language(message):
            crisis = build_crisis_response()
            response = CoachingResponse(
                session_id=session,
                lane=WELLBEING_LANE,
                ask=[],
                listen="Thank you for trusting me with this.",
                reflect="This sounds beyond what coaching alone can hold safely.",
                suggest=["Please contact one of the crisis resources listed now."],
                crisis=crisis,
            )
            return response

        belief_reframe = detect_limiting_belief(message)
        ask = [
            "What felt hardest about that today?",
            "What would a slightly easier version look like?",
            "What support would help you most right now?",
        ]
        listen = "Thanks for sharing that. It makes sense you would feel this way."
        reflect = f"You mentioned: {message.strip()[:240]}"
        if belief_reframe:
            reflect += f" A thought to sit with: {belief_reframe}"
        if context:
            reflect += f" (Context you shared: {context[:120]})"

        suggest = [
            "Pick one small action you can do in the next 24 hours.",
            "Notice one thing that went okay today, however small.",
        ]
        if negative_checkin_streak >= 3:
            suggest.append(PROFESSIONAL_HELP_NOTE)

        response = CoachingResponse(
            session_id=session,
            lane=WELLBEING_LANE,
            ask=ask,
            listen=listen,
            reflect=reflect,
            suggest=suggest,
            crisis=CrisisResponse(detected=False),
            suggest_professional_help=negative_checkin_streak >= 3,
        )
        return response

    async def coach_and_store(
        self,
        message: str,
        *,
        session_id: str | None = None,
        context: str = "",
        negative_checkin_streak: int = 0,
    ) -> CoachingResponse:
        response = self.coach(
            message,
            session_id=session_id,
            context=context,
            negative_checkin_streak=negative_checkin_streak,
            store=False,
        )
        payload = response.to_dict()
        payload["stored_at"] = datetime.now(UTC).isoformat()
        payload["user_message"] = message
        response.vault_item_id = await store_coaching_turn(self.user_id, payload)
        return response

    def shares_with_work_agents(self) -> bool:
        return False
