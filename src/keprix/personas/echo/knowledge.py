"""Business knowledge and caller Q&A for ECHO."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from keprix.memory.rag.retriever import RagRetriever
from keprix.personas.echo.persona import ECHO_PERSONA

UNKNOWN_ANSWER = "Let me find that out for you. I can have someone call you back with the details."

FAQ_TOPIC_PATTERNS: dict[str, tuple[str, ...]] = {
    "hours": (r"\b(hours|open|opening|close|closing|when are you)\b",),
    "location": (r"\b(where are you|address|directions|located|find you)\b",),
    "services": (r"\b(services|what do you do|offerings|products)\b",),
    "pricing": (r"\b(price|pricing|cost|how much|fee)\b",),
    "parking": (r"\b(parking|park|access|wheelchair)\b",),
}


@dataclass(slots=True)
class BusinessProfile:
    business_name: str = "Your Business"
    hours: str = "Monday to Friday, 9am to 5pm"
    location: str = ""
    services: str = ""
    pricing_note: str = "Please speak with our team for a tailored quote."
    parking_note: str = ""
    primary_language: str = "en-GB"
    timezone: str = "Europe/London"

    def to_dict(self) -> dict[str, Any]:
        return {
            "business_name": self.business_name,
            "hours": self.hours,
            "location": self.location,
            "services": self.services,
            "pricing_note": self.pricing_note,
            "parking_note": self.parking_note,
            "primary_language": self.primary_language,
            "timezone": self.timezone,
        }


@dataclass
class FaqAnswer:
    question: str
    answer: str
    source: str
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "source": self.source,
            "confidence": self.confidence,
        }


class EchoKnowledge:
    """Loads FAQ from RAG and configured business profile."""

    def __init__(
        self,
        *,
        workspace_id: str = "default",
        user_id: str = "default",
        profile: BusinessProfile | None = None,
        retriever: RagRetriever | None = None,
    ) -> None:
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.persona = ECHO_PERSONA
        self.profile = profile or BusinessProfile()
        self._retriever = retriever or RagRetriever()

    def detect_topic(self, question: str) -> str | None:
        lowered = question.lower()
        for topic, patterns in FAQ_TOPIC_PATTERNS.items():
            if any(re.search(pattern, lowered) for pattern in patterns):
                return topic
        return None

    def answer_from_profile(self, question: str) -> FaqAnswer | None:
        topic = self.detect_topic(question)
        if topic == "hours" and self.profile.hours:
            return FaqAnswer(question, f"Our hours are {self.profile.hours}.", "profile")
        if topic == "location" and self.profile.location:
            return FaqAnswer(question, f"We are located at {self.profile.location}.", "profile")
        if topic == "services" and self.profile.services:
            return FaqAnswer(question, self.profile.services, "profile")
        if topic == "pricing" and self.profile.pricing_note:
            return FaqAnswer(question, self.profile.pricing_note, "profile")
        if topic == "parking" and self.profile.parking_note:
            return FaqAnswer(question, self.profile.parking_note, "profile")
        return None

    async def search_rag(self, question: str, *, limit: int = 3) -> list[dict[str, Any]]:
        try:
            return await self._retriever.hybrid_search(self.user_id, question, limit=limit)
        except Exception:
            return await self._retriever.search(self.user_id, question, limit=limit)

    async def answer_question(self, question: str) -> FaqAnswer:
        profile_answer = self.answer_from_profile(question)
        if profile_answer is not None:
            return profile_answer

        hits = await self.search_rag(question)
        if hits:
            best = hits[0]
            content = str(best.get("content") or "").strip()
            if content:
                return FaqAnswer(
                    question=question,
                    answer=content,
                    source=str(best.get("source") or "rag"),
                    confidence=float(best.get("score") or 0.5),
                )

        static = self.persona.load_prompt("faq.md")
        topic = self.detect_topic(question)
        if topic and topic in static.lower():
            return FaqAnswer(question, UNKNOWN_ANSWER, "faq_prompt", confidence=0.2)

        return FaqAnswer(question, UNKNOWN_ANSWER, "fallback", confidence=0.0)

    def list_static_topics(self) -> list[str]:
        return list(FAQ_TOPIC_PATTERNS)
