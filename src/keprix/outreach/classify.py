"""Reply classification for outreach (heuristic + optional LLM)."""

from __future__ import annotations

import json
import re
from typing import Any

CLASSIFICATIONS = (
    "interested",
    "booking_intent",
    "question",
    "objection",
    "not_interested",
    "not_now",
    "unsubscribe",
    "ooo",
)

_CLASS_TO_LEAD_STATUS = {
    "interested": "interested",
    "booking_intent": "booking",
    "question": "replied",
    "objection": "replied",
    "not_interested": "lost",
    "not_now": "not_now",
    "unsubscribe": "unsubscribed",
    "ooo": "replied",
}

_CLASS_TO_ENROLLMENT_STATUS = {
    "unsubscribe": "stopped_unsubscribe",
    "booking_intent": "stopped_booking",
    "not_interested": "stopped_reply",
    "interested": "stopped_reply",
    "question": None,  # keep active unless stop_on_reply
    "objection": None,
    "not_now": None,
    "ooo": None,
}


def lead_status_for_classification(classification: str) -> str:
    return _CLASS_TO_LEAD_STATUS.get(classification, "replied")


def enrollment_stop_status(classification: str, sequence: dict[str, Any]) -> str | None:
    """Return enrollment status to set, or None to leave active."""
    if classification == "unsubscribe" and sequence.get("stop_on_unsubscribe", True):
        return "stopped_unsubscribe"
    if classification == "booking_intent" and sequence.get("stop_on_booking", True):
        return "stopped_booking"
    if classification in ("interested", "not_interested", "question", "objection") and sequence.get(
        "stop_on_reply", True
    ):
        # OOO / not_now keep running; interested/not_interested/question/objection stop
        if classification in ("interested", "not_interested"):
            return "stopped_reply"
        if classification in ("question", "objection"):
            return "stopped_reply"
    mapped = _CLASS_TO_ENROLLMENT_STATUS.get(classification)
    return mapped


def classify_reply_heuristic(subject: str, body: str) -> dict[str, Any]:
    text = f"{subject or ''}\n{body or ''}".lower()

    patterns: list[tuple[str, tuple[str, ...], float]] = [
        ("unsubscribe", ("unsubscribe", "remove me", "stop emailing", "opt out", "opt-out"), 0.95),
        ("ooo", ("out of office", "auto-reply", "automatic reply", "away from", "on leave"), 0.9),
        (
            "booking_intent",
            ("book a call", "schedule a", "calendar link", "set up a meeting", "available for a call", "happy to meet"),
            0.9,
        ),
        ("interested", ("interested", "sounds good", "tell me more", "keen", "let's talk", "lets talk"), 0.8),
        ("objection", ("too expensive", "not the right time", "already have", "budget", "concern"), 0.75),
        ("not_interested", ("not interested", "no thanks", "please don't", "do not contact"), 0.9),
        ("not_now", ("not now", "maybe later", "next quarter", "circle back", "in a few months"), 0.8),
        ("question", ("?", "how does", "what is", "can you", "pricing", "how much"), 0.7),
    ]

    for label, needles, conf in patterns:
        if any(n in text for n in needles):
            return {"classification": label, "confidence": conf, "method": "heuristic"}

    if re.search(r"\?", text):
        return {"classification": "question", "confidence": 0.6, "method": "heuristic"}

    return {"classification": "question", "confidence": 0.4, "method": "heuristic"}


async def classify_reply_llm(subject: str, body: str, from_address: str = "") -> dict[str, Any]:
    """Prefer LLM; fall back to heuristic."""
    heuristic = classify_reply_heuristic(subject, body)
    try:
        from keprix.email.llm import llm_complete

        prompt = (
            "Classify this outreach reply. Respond with JSON only:\n"
            '{"classification": one of '
            + json.dumps(list(CLASSIFICATIONS))
            + ', "confidence": 0-1}\n\n'
            f"From: {from_address}\nSubject: {subject}\n\n{body[:4000]}"
        )
        raw = await llm_complete(
            prompt,
            system="You classify sales outreach replies. Output valid JSON only.",
        )
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(raw[start : end + 1])
            label = str(data.get("classification") or "").strip().lower()
            if label in CLASSIFICATIONS:
                conf = float(data.get("confidence") or 0.7)
                return {"classification": label, "confidence": conf, "method": "llm"}
    except Exception:
        pass
    return heuristic


def classify_reply_sync(subject: str, body: str, from_address: str = "") -> dict[str, Any]:
    """Sync entry used by tools; tries LLM via asyncio when possible."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(
                lambda: asyncio.run(classify_reply_llm(subject, body, from_address))
            ).result()
    try:
        return asyncio.run(classify_reply_llm(subject, body, from_address))
    except Exception:
        return classify_reply_heuristic(subject, body)
