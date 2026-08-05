"""Keprix agent wrapper for phone voice."""

from __future__ import annotations

import re

from keprix.voice.caller_context import CallerContext
from keprix.voice.personas.receptionist import should_escalate
from keprix.voice.providers.llm.base import VoiceAgentResponse
from keprix.voice.session import VoiceSession


class KeprixVoiceAgent:
    def __init__(self, *, business_name: str = "the business") -> None:
        self.business_name = business_name
        self.is_speaking = False

    async def load_context(self, caller: str) -> CallerContext:
        return await CallerContext.from_phone(caller)

    async def respond(self, text: str, session: VoiceSession, context: CallerContext) -> VoiceAgentResponse:
        lowered = text.lower()
        if should_escalate(text):
            session.escalated = True
            return VoiceAgentResponse(
                text="I understand this is urgent. Let me connect you with someone who can help right away.",
                action="escalate",
            )
        if "book" in lowered or "appointment" in lowered or "viewing" in lowered:
            session.topic = "booking"
            session.appointments_booked += 1
            return VoiceAgentResponse(
                text="So that's Tuesday at 2pm for a viewing. Is that correct? I can send a confirmation once you confirm.",
                action="confirm_booking",
            )
        if context.name and context.previous_calls:
            last = context.previous_calls[-1]
            return VoiceAgentResponse(
                text=f"Welcome back, {context.name}. I have your last call about {last.topic}. How can I help today?",
                action="reply",
            )
        name_match = re.search(r"my name is ([a-zA-Z ]+)", text, re.I)
        if name_match:
            context.name = name_match.group(1).strip()
        return VoiceAgentResponse(text=f"Got it. Aiva speaking for {self.business_name}. How can I help?", action="reply")

    async def save_to_memory(self, session: VoiceSession, text: str, response: VoiceAgentResponse) -> None:
        context = await CallerContext.from_phone(session.caller)
        await context.save_summary(session, outcome=response.action, notes=text)
