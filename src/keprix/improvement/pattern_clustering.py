"""Small deterministic clustering for repeated session tasks."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from keprix.improvement.task_extractor import SessionTaskEvidence


@dataclass
class RepeatedTask:
    description: str
    occurrence_count: int
    sessions: list[str]
    tools_used: list[str] = field(default_factory=list)
    estimated_tokens_per_run: int = 0
    confidence: float = 0.0


def normalize_task(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.lower()).strip()
    cleaned = re.sub(r"[^a-z0-9\s/-]", "", cleaned)
    words = cleaned.split()
    return " ".join(words[:10])


def cluster_repeated_tasks(evidence: list[SessionTaskEvidence], *, min_occurrences: int = 3) -> list[RepeatedTask]:
    buckets: dict[str, list[SessionTaskEvidence]] = defaultdict(list)
    for item in evidence:
        key = normalize_task(item.description)
        if len(key) >= 12:
            buckets[key].append(item)

    repeated: list[RepeatedTask] = []
    for items in buckets.values():
        if len(items) < min_occurrences:
            continue
        tools: list[str] = []
        for item in items:
            tools.extend(item.tools_used)
        avg_tokens = int(sum(item.estimated_tokens for item in items) / max(1, len(items)))
        confidence = min(0.95, 0.55 + (len(items) * 0.1))
        repeated.append(
            RepeatedTask(
                description=items[0].description,
                occurrence_count=len(items),
                sessions=[item.session_id for item in items],
                tools_used=sorted(set(tools)),
                estimated_tokens_per_run=avg_tokens,
                confidence=round(confidence, 2),
            )
        )
    return sorted(repeated, key=lambda item: (-item.occurrence_count, item.description))
