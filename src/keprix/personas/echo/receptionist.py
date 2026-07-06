"""Inbound call handling, routing, and escalation for ECHO."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from keprix.contacts.store import get_contact_store
from keprix.personas.echo.knowledge import BusinessProfile, EchoKnowledge
from keprix.personas.echo.persona import ECHO_PERSONA
from keprix.personas.echo.scheduler import EchoScheduler
from keprix.security.vault_service import get_vault_service

RING_TARGET_SECONDS = 12

EMERGENCY_PATTERNS = (
    r"\b(heart attack|can't breathe|cannot breathe|stroke|unconscious)\b",
    r"\b(emergency|ambulance|police|fire|999|911|112)\b",
    r"\b(someone is hurt|injured badly|medical emergency)\b",
)

LEGAL_THREAT_PATTERNS = (
    r"\b(sue you|lawsuit|solicitor|lawyer|legal action|court)\b",
    r"\b(breach of contract|data breach|gdpr complaint|ico)\b",
)

ANGRY_PATTERNS = (
    r"\b(furious|disgusting|useless|idiot|scam|refund now)\b",
    r"\b(threaten|report you|never again)\b",
)

COMPLEX_SALE_PATTERNS = (
    r"\b(enterprise|volume discount|negotiate|custom contract|procurement)\b",
    r"\b(rfp|tender|annual licence|annual license)\b",
)


class CallPhase(StrEnum):
    GREET = "greet"
    IDENTIFY = "identify"
    RESOLVE = "resolve"
    CLOSE = "close"


class EscalationType(StrEnum):
    NONE = "none"
    EMERGENCY = "emergency"
    LEGAL = "legal"
    ANGRY = "angry"
    COMPLEX_SALE = "complex_sale"


@dataclass(slots=True)
class CallerIdentity:
    name: str = ""
    phone: str = ""
    email: str = ""
    existing_contact: bool = False
    contact_id: str | None = None
    purpose: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "existing_contact": self.existing_contact,
            "contact_id": self.contact_id,
            "purpose": self.purpose,
        }


@dataclass
class CallSession:
    call_id: str
    provider: str
    phase: CallPhase = CallPhase.GREET
    caller: CallerIdentity = field(default_factory=CallerIdentity)
    transcript: list[str] = field(default_factory=list)
    escalation: EscalationType = EscalationType.NONE
    route_to: str | None = None
    booking_event_id: str | None = None
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "provider": self.provider,
            "phase": self.phase.value,
            "caller": self.caller.to_dict(),
            "transcript": list(self.transcript),
            "escalation": self.escalation.value,
            "route_to": self.route_to,
            "booking_event_id": self.booking_event_id,
            "started_at": self.started_at,
        }


@dataclass
class CallTurn:
    session_id: str
    reply: str
    phase: CallPhase
    escalation: EscalationType
    action: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "reply": self.reply,
            "phase": self.phase.value,
            "escalation": self.escalation.value,
            "action": self.action,
            "metadata": dict(self.metadata),
        }


class EchoReceptionist:
    """Handles voice webhooks, caller routing, and CRM logging."""

    def __init__(
        self,
        *,
        workspace_id: str = "default",
        user_id: str = "default",
        profile: BusinessProfile | None = None,
        knowledge: EchoKnowledge | None = None,
        scheduler: EchoScheduler | None = None,
    ) -> None:
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.persona = ECHO_PERSONA
        self.profile = profile or BusinessProfile()
        self.knowledge = knowledge or EchoKnowledge(
            workspace_id=workspace_id,
            user_id=user_id,
            profile=self.profile,
        )
        self.scheduler = scheduler or EchoScheduler(workspace_id=workspace_id, user_id=user_id)
        self._sessions: dict[str, CallSession] = {}

    def greeting(self, *, caller_name: str = "") -> str:
        hour = datetime.now(UTC).hour
        if hour < 12:
            period = "morning"
        elif hour < 17:
            period = "afternoon"
        else:
            period = "evening"
        if caller_name:
            return f"Good {period}, {self.profile.business_name}. Welcome back, {caller_name}. How can I help?"
        return f"Good {period}, {self.profile.business_name}, this is ECHO. How can I help?"

    def detect_escalation(self, text: str) -> EscalationType:
        lowered = text.lower()
        if any(re.search(pattern, lowered) for pattern in EMERGENCY_PATTERNS):
            return EscalationType.EMERGENCY
        if any(re.search(pattern, lowered) for pattern in LEGAL_THREAT_PATTERNS):
            return EscalationType.LEGAL
        if any(re.search(pattern, lowered) for pattern in ANGRY_PATTERNS):
            return EscalationType.ANGRY
        if any(re.search(pattern, lowered) for pattern in COMPLEX_SALE_PATTERNS):
            return EscalationType.COMPLEX_SALE
        return EscalationType.NONE

    def parse_voice_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        provider = str(payload.get("provider") or "twilio").lower()
        call_id = str(
            payload.get("CallSid")
            or payload.get("call_id")
            or payload.get("uuid")
            or uuid4()
        )
        caller_phone = str(payload.get("From") or payload.get("caller") or payload.get("from") or "")
        speech = str(payload.get("SpeechResult") or payload.get("transcript") or payload.get("text") or "")
        return {
            "provider": provider,
            "call_id": call_id,
            "caller_phone": caller_phone,
            "speech": speech.strip(),
        }

    def build_voice_gateway_response(self, reply: str, *, gather: bool = True) -> dict[str, Any]:
        response: dict[str, Any] = {
            "say": reply,
            "voice": "Polly.Amy",
            "language": self.profile.primary_language,
            "ring_within_seconds": RING_TARGET_SECONDS,
        }
        if gather:
            response["gather"] = True
        return response

    async def identify_caller(self, phone: str, *, name: str = "") -> CallerIdentity:
        identity = CallerIdentity(phone=phone, name=name.strip())
        if not phone and not name:
            return identity
        store = get_contact_store()
        rows = await store.list_contacts(query=phone or name, limit=5, offset=0)
        for row in rows:
            phones = {str(item.get("number") or "") for item in row.phones}
            if phone and phone in phones:
                identity.existing_contact = True
                identity.contact_id = row.id
                identity.name = identity.name or row.display_name
                identity.email = next(
                    (str(item.get("address") or "") for item in row.emails if item.get("primary")),
                    identity.email,
                )
                break
            if name and name.lower() in row.display_name.lower():
                identity.existing_contact = True
                identity.contact_id = row.id
                identity.name = row.display_name
                break
        return identity

    def _extract_name(self, text: str) -> str:
        match = re.search(r"\b(?:my name is|this is|i am|i'm)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text, re.I)
        return match.group(1).strip() if match else ""

    def _wants_booking(self, text: str) -> bool:
        lowered = text.lower()
        return any(word in lowered for word in ("book", "appointment", "meeting", "schedule", "reschedule", "cancel"))

    async def handle_inbound_webhook(self, payload: dict[str, Any]) -> CallTurn:
        parsed = self.parse_voice_webhook(payload)
        call_id = parsed["call_id"]
        session = self._sessions.get(call_id)
        if session is None:
            caller = await self.identify_caller(parsed["caller_phone"])
            session = CallSession(call_id=call_id, provider=parsed["provider"], caller=caller)
            self._sessions[call_id] = session

        speech = parsed["speech"]
        if not speech:
            reply = self.greeting(caller_name=session.caller.name)
            session.phase = CallPhase.IDENTIFY
            return CallTurn(
                session_id=call_id,
                reply=reply,
                phase=session.phase,
                escalation=EscalationType.NONE,
                action="greet",
                metadata={"voice": self.build_voice_gateway_response(reply)},
            )

        session.transcript.append(speech)
        escalation = self.detect_escalation(speech)
        session.escalation = escalation

        if escalation == EscalationType.EMERGENCY:
            reply = (
                "This sounds like an emergency. Please hang up and call 999 in the UK "
                "or your local emergency number immediately."
            )
            session.route_to = "emergency_services"
            session.phase = CallPhase.CLOSE
            await self.log_interaction(session, summary="Emergency escalation")
            return CallTurn(
                session_id=call_id,
                reply=reply,
                phase=session.phase,
                escalation=escalation,
                action="escalate_emergency",
                metadata={"flag_warden": False},
            )

        if escalation == EscalationType.LEGAL:
            reply = (
                "I understand this is a serious matter. I will note the details and have a senior "
                "team member call you back shortly."
            )
            session.route_to = "human_legal"
            session.phase = CallPhase.CLOSE
            await self.log_interaction(session, summary="Legal threat flagged for WARDEN review")
            return CallTurn(
                session_id=call_id,
                reply=reply,
                phase=session.phase,
                escalation=escalation,
                action="escalate_legal",
                metadata={"flag_warden": True, "handoff": "WARDEN"},
            )

        if escalation == EscalationType.ANGRY:
            reply = (
                "I am sorry you have had that experience. I can arrange for someone to call you back "
                "within fifteen minutes."
            )
            session.route_to = "human_callback_15m"
            session.phase = CallPhase.CLOSE
            await self.log_interaction(session, summary="Angry caller; callback within 15 minutes")
            return CallTurn(
                session_id=call_id,
                reply=reply,
                phase=session.phase,
                escalation=escalation,
                action="escalate_callback",
            )

        if not session.caller.name:
            extracted = self._extract_name(speech)
            if extracted:
                session.caller.name = extracted
                session.phase = CallPhase.RESOLVE
                reply = f"Thank you, {extracted}. How can I help you today?"
                return CallTurn(
                    session_id=call_id,
                    reply=reply,
                    phase=session.phase,
                    escalation=EscalationType.NONE,
                    action="identify",
                )

        if self._wants_booking(speech):
            session.caller.purpose = speech
            slots = self.scheduler.find_available_slots(count=2)
            if not slots:
                reply = "I do not have availability in the next few days. Shall I arrange a callback?"
                action = "booking_unavailable"
            else:
                options = " or ".join(slot.start_at.strftime("%A at %H:%M") for slot in slots)
                reply = f"I can book an appointment. I have {options} available. Which works better?"
                action = "offer_slots"
                session.phase = CallPhase.RESOLVE
            return CallTurn(
                session_id=call_id,
                reply=reply,
                phase=session.phase,
                escalation=escalation,
                action=action,
                metadata={"slots": [slot.to_dict() for slot in slots]},
            )

        if escalation == EscalationType.COMPLEX_SALE:
            session.route_to = "sales_callback"
            reply = "That sounds like something our team should discuss with you directly. I will book a callback."
            session.phase = CallPhase.CLOSE
            await self.log_interaction(session, summary="Complex sale routed to callback")
            return CallTurn(
                session_id=call_id,
                reply=reply,
                phase=session.phase,
                escalation=escalation,
                action="route_sales",
            )

        faq = await self.knowledge.answer_question(speech)
        session.phase = CallPhase.RESOLVE
        reply = faq.answer
        await self.log_interaction(session, summary=f"FAQ: {speech[:120]}")
        return CallTurn(
            session_id=call_id,
            reply=reply,
            phase=session.phase,
            escalation=escalation,
            action="answer_faq",
            metadata={"faq": faq.to_dict()},
        )

    async def book_from_session(
        self,
        call_id: str,
        *,
        slot_index: int = 0,
        title: str = "Phone appointment",
    ) -> CallTurn:
        session = self._sessions.get(call_id)
        if session is None:
            return CallTurn(
                session_id=call_id,
                reply="I could not find this call session.",
                phase=CallPhase.CLOSE,
                escalation=EscalationType.NONE,
                action="error",
            )
        slots = self.scheduler.find_available_slots(count=slot_index + 1)
        if len(slots) <= slot_index:
            return CallTurn(
                session_id=call_id,
                reply="That slot is no longer available.",
                phase=session.phase,
                escalation=EscalationType.NONE,
                action="booking_failed",
            )
        slot = slots[slot_index]
        booking = self.scheduler.book_appointment(
            title=title,
            start_at=slot.start_at,
            caller_name=session.caller.name or "Caller",
            caller_phone=session.caller.phone,
            caller_email=session.caller.email,
            description=session.caller.purpose,
        )
        if booking.booked:
            session.booking_event_id = booking.event_id
            session.phase = CallPhase.CLOSE
            await self.log_interaction(session, summary=f"Booked appointment {booking.event_id}")
        return CallTurn(
            session_id=call_id,
            reply=booking.message,
            phase=session.phase,
            escalation=EscalationType.NONE,
            action="book" if booking.booked else "booking_failed",
            metadata={"booking": booking.to_dict()},
        )

    def transfer_summary(self, session: CallSession) -> dict[str, Any]:
        return {
            "call_id": session.call_id,
            "caller": session.caller.to_dict(),
            "purpose": session.caller.purpose,
            "escalation": session.escalation.value,
            "transcript": list(session.transcript),
            "route_to": session.route_to,
            "message": (
                f"Caller {session.caller.name or 'unknown'} ({session.caller.phone}) "
                f"needs {session.route_to or 'human assistance'}."
            ),
        }

    async def log_interaction(self, session: CallSession, *, summary: str) -> dict[str, Any]:
        store = get_contact_store()
        note_line = f"[ECHO {datetime.now(UTC).isoformat()}] {summary}"
        if session.caller.contact_id:
            contact = await store.get(session.caller.contact_id)
            if contact:
                merged_notes = "\n".join(part for part in [contact.notes, note_line] if part)
                await store.update(session.caller.contact_id, {"notes": merged_notes})
                return {"logged": True, "contact_id": session.caller.contact_id}
        if session.caller.phone or session.caller.name:
            created = await store.create(
                {
                    "display_name": session.caller.name or session.caller.phone or "Unknown caller",
                    "phones": [{"number": session.caller.phone, "primary": True}] if session.caller.phone else [],
                    "emails": [{"address": session.caller.email, "primary": True}] if session.caller.email else [],
                    "notes": note_line,
                },
                source="echo",
            )
            session.caller.contact_id = created.id
            session.caller.existing_contact = False
            return {"logged": True, "contact_id": created.id, "created": True}
        return {"logged": False}

    async def store_call_recording(self, audio_bytes: bytes, *, call_id: str) -> dict[str, Any]:
        vault = get_vault_service()
        encoded = base64.b64encode(audio_bytes).decode("ascii")
        item = await vault.create_item(
            self.user_id,
            label=f"ECHO call recording {call_id}",
            category="echo-call-recording",
            value=encoded,
            tags=["echo", "call-recording", call_id],
        )
        return {"vault_item_id": item.id, "encrypted": True, "call_id": call_id}

    def get_session(self, call_id: str) -> CallSession | None:
        return self._sessions.get(call_id)

    def session_snapshot(self) -> list[dict[str, Any]]:
        return [session.to_dict() for session in self._sessions.values()]
