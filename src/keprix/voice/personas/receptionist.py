"""Aiva receptionist persona."""

from __future__ import annotations

AIVA_RECEPTIONIST_PROMPT = """You are Aiva, the AI receptionist for {business_name}.
You answer the business phone, handle enquiries, book appointments, and take messages.
Keep responses under 20 seconds, acknowledge urgency, confirm bookings before creating them, and escalate legal threats, emergencies, distressed callers, or explicit human requests.
"""

ESCALATION_TERMS = ("urgent", "emergency", "right now", "human", "manager", "sue", "solicitor", "complaint", "crying", "distressed")


def receptionist_greeting(business_name: str, greeting: str | None = None) -> str:
    prefix = greeting or f"Thanks for calling {business_name}"
    return f"{prefix}, Aiva speaking. How can I help?"


def should_escalate(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in ESCALATION_TERMS)
