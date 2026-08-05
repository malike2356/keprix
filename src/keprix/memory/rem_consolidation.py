"""REM consolidation after session end."""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from keprix.memory.episodic.store import EpisodicStore, create_episodic_store

logger = logging.getLogger(__name__)

FACT_PATTERNS = [
    re.compile(r"\bmy name is\b", re.I),
    re.compile(r"\bi (work|live|prefer|always|never|usually)\b", re.I),
    re.compile(r"\bremember\b", re.I),
    re.compile(r"\bfavorite\b", re.I),
    re.compile(r"\btimezone\b", re.I),
    re.compile(r"\bdeadline\b", re.I),
    re.compile(r"\bgoal\b", re.I),
]

FLUFF_PATTERNS = [
    re.compile(r"^(hi|hello|thanks|thank you|ok|sure)\b", re.I),
    re.compile(r"\?\s*$"),
    re.compile(r"^how can i help", re.I),
]


def distill_episode_content(content: str) -> str:
    line = " ".join(content.split())
    if len(line) <= 320:
        return line
    return f"{line[:317]}..."


def infer_topic_tags(content: str) -> list[str]:
    tags: list[str] = []
    lower = content.lower()
    for keyword in ("work", "family", "project", "preference", "deadline", "contact"):
        if keyword in lower:
            tags.append(keyword)
    return tags


def score_episode(
    *,
    role: str,
    content: str,
    priority: int = 0,
    access_count: int = 0,
    created_at: datetime | None = None,
) -> float:
    text = content.strip()
    if len(text) < 12:
        return 0.0

    score = 0.2
    if role == "user":
        score += 0.15
    if 40 <= len(text) <= 500:
        score += 0.1
    if len(text) > 900:
        score -= 0.1
    if any(pattern.search(text) for pattern in FACT_PATTERNS):
        score += 0.22
    if any(pattern.search(text) for pattern in FLUFF_PATTERNS):
        score -= 0.25
    if priority > 0:
        score += min(priority * 0.05, 0.2)
    score += min(access_count * 0.06, 0.24)

    if created_at is not None:
        age_hours = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
        if 1 <= age_hours <= 72:
            score += 0.05
        if age_hours > 168:
            score -= 0.08

    return max(0.0, min(1.0, round(score, 3)))


def extract_durable_facts(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for message in messages:
        role = str(message.get("role", "user"))
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        score = score_episode(role=role, content=content)
        if score < float(os.getenv("KEPRIX_REM_PROMOTE_THRESHOLD", "0.65")):
            continue
        distilled = distill_episode_content(content)
        facts.append(
            {
                "content": distilled,
                "tags": infer_topic_tags(distilled),
                "score": score,
                "role": role,
            }
        )
    return facts


class RemConsolidator:
    def __init__(self, store: EpisodicStore | None = None) -> None:
        self.store = store or create_episodic_store()

    async def consolidate_session(
        self,
        *,
        user_id: str,
        session_id: str,
        messages: list[dict[str, Any]],
    ) -> list[str]:
        saved_ids: list[str] = []
        for fact in extract_durable_facts(messages):
            memory_id = await self.store.save(
                user_id,
                fact["content"],
                metadata={
                    "session_id": session_id,
                    "tags": list({*(fact["tags"] or []), "rem"}),
                    "rem_score": fact["score"],
                    "source_role": fact["role"],
                    "source": "rem",
                    "memory_type": "preference" if "prefer" in fact["content"].lower() else "semantic",
                    "belief_state": "active",
                    "confidence": fact["score"],
                    "modality": "text",
                    "model_side": "user",
                },
            )
            saved_ids.append(memory_id)
        logger.info(
            "REM consolidation saved %d memories for user=%s session=%s",
            len(saved_ids),
            user_id,
            session_id,
        )
        return saved_ids

    async def prune_expired(self, user_id: str) -> int:
        before = await self.store.list_all(user_id)
        # Postgres/in-memory stores already filter expired rows on read.
        return len(before)


async def run_session_consolidation(
    *,
    user_id: str,
    session_id: str,
    messages: list[dict[str, Any]],
) -> list[str]:
    consolidator = RemConsolidator()
    return await consolidator.consolidate_session(
        user_id=user_id,
        session_id=session_id,
        messages=messages,
    )
