"""Cheap ambient message classifier (Prompt 45)."""

from __future__ import annotations

import json
import os
import re
from typing import Awaitable, Callable

from keprix.backend.messaging.schemas import AmbientProcessingResult, InboundMessage

ClassifierFn = Callable[[str, InboundMessage], Awaitable[AmbientProcessingResult]]

_DIRECT_QUESTION_PATTERNS = [
    re.compile(r"\?\s*$"),
    re.compile(r"\b(please|can you|could you|help me|what is|how do)\b", re.IGNORECASE),
    re.compile(r"\b(@?bot|assistant|keprix|agent)\b", re.IGNORECASE),
]


async def heuristic_classify(context: str, message: InboundMessage) -> AmbientProcessingResult:
    text = message.text.strip()
    should_reply = message.is_mention or any(pattern.search(text) for pattern in _DIRECT_QUESTION_PATTERNS)
    context_notes: list[str] = []
    memory_candidates: list[str] = []
    if text:
        context_notes.append(text[:120])
    role_match = re.search(r"\b(I am|I'm|My name is)\s+([A-Za-z][A-Za-z\s'-]{1,40})", text, re.IGNORECASE)
    if role_match:
        memory_candidates.append(role_match.group(0).strip())
    return AmbientProcessingResult(
        should_reply=should_reply,
        context_notes=context_notes[:3],
        memory_candidates=memory_candidates[:2],
    )


async def llm_classify(context: str, message: InboundMessage) -> AmbientProcessingResult:
    prompt = (
        "You are monitoring a group chat as a background observer. "
        "Classify this message:\n\n"
        f"{context}\n\n"
        "Return JSON:\n"
        "{\n"
        '  "should_reply": true|false,\n'
        '  "context_notes": [],\n'
        '  "memory_candidates": []\n'
        "}"
    )
    model = os.environ.get("KEPRIX_AMBIENT_MODEL", "fast")
    try:
        from keprix.backend.messaging.llm_client import complete_json

        parsed = await complete_json(prompt, model=model)
        return AmbientProcessingResult(
            should_reply=bool(parsed.get("should_reply", False)),
            context_notes=[str(item) for item in parsed.get("context_notes", [])][:3],
            memory_candidates=[str(item) for item in parsed.get("memory_candidates", [])][:2],
        )
    except Exception:
        return await heuristic_classify(context, message)


async def default_classifier(context: str, message: InboundMessage) -> AmbientProcessingResult:
    if os.environ.get("KEPRIX_AMBIENT_USE_LLM", "").lower() in {"1", "true", "yes", "on"}:
        return await llm_classify(context, message)
    return await heuristic_classify(context, message)
