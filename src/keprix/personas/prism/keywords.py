"""Keyword research, clustering, and gap analysis for PRISM."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from keprix.compat import StrEnum
from typing import Any

from keprix.personas.prism.persona import PRISM_PERSONA


class KeywordIntent(StrEnum):
    INFORMATIONAL = "informational"
    NAVIGATIONAL = "navigational"
    COMMERCIAL = "commercial"
    TRANSACTIONAL = "transactional"


INTENT_MODIFIERS: dict[KeywordIntent, tuple[str, ...]] = {
    KeywordIntent.INFORMATIONAL: ("how to", "what is", "guide", "tips", "examples", "checklist"),
    KeywordIntent.NAVIGATIONAL: ("login", "pricing", "official", "website", "portal"),
    KeywordIntent.COMMERCIAL: ("best", "vs", "review", "comparison", "top", "alternative"),
    KeywordIntent.TRANSACTIONAL: ("buy", "hire", "book", "demo", "quote", "pricing plans"),
}


@dataclass(slots=True)
class KeywordEntry:
    keyword: str
    volume: int
    difficulty: int
    intent: str
    cpc: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "keyword": self.keyword,
            "volume": self.volume,
            "difficulty": self.difficulty,
            "intent": self.intent,
            "cpc": self.cpc,
        }


@dataclass(slots=True)
class KeywordCluster:
    cluster_id: str
    theme: str
    keywords: list[KeywordEntry] = field(default_factory=list)
    total_volume: int = 0
    avg_difficulty: float = 0.0
    dominant_intent: str = KeywordIntent.INFORMATIONAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "theme": self.theme,
            "keywords": [entry.to_dict() for entry in self.keywords],
            "total_volume": self.total_volume,
            "avg_difficulty": round(self.avg_difficulty, 1),
            "dominant_intent": self.dominant_intent,
        }


@dataclass
class GapAnalysisResult:
    seed: str
    missing_keywords: list[KeywordEntry] = field(default_factory=list)
    shared_keywords: list[KeywordEntry] = field(default_factory=list)
    opportunity_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "missing_keywords": [entry.to_dict() for entry in self.missing_keywords],
            "shared_keywords": [entry.to_dict() for entry in self.shared_keywords],
            "opportunity_score": round(self.opportunity_score, 2),
        }


def _stable_int(seed: str, keyword: str, upper: int) -> int:
    digest = hashlib.sha256(f"{seed}:{keyword}".encode()).hexdigest()
    return int(digest[:8], 16) % upper


def classify_intent(keyword: str) -> str:
    lowered = keyword.lower()
    for intent, modifiers in INTENT_MODIFIERS.items():
        if any(modifier in lowered for modifier in modifiers):
            return intent
    if re.search(r"\b(near me|in \w+)\b", lowered):
        return KeywordIntent.TRANSACTIONAL
    return KeywordIntent.INFORMATIONAL


def _estimate_metrics(seed: str, keyword: str) -> tuple[int, int, float]:
    volume = 120 + _stable_int(seed, keyword, 9800)
    difficulty = 15 + _stable_int(seed, keyword + ":kd", 75)
    cpc = round(0.4 + _stable_int(seed, keyword + ":cpc", 1200) / 100.0, 2)
    return volume, difficulty, cpc


def _stem(keyword: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", keyword.lower())
    if not tokens:
        return keyword.lower()
    return tokens[0]


class PrismKeywords:
    def __init__(self, *, workspace_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.persona = PRISM_PERSONA

    def research_keywords(self, seed: str, *, limit: int = 12) -> list[KeywordEntry]:
        seed = seed.strip()
        if not seed:
            return []

        variants: list[str] = [seed]
        for modifier in INTENT_MODIFIERS[KeywordIntent.INFORMATIONAL][:3]:
            variants.append(f"{modifier} {seed}")
        for modifier in INTENT_MODIFIERS[KeywordIntent.COMMERCIAL][:2]:
            variants.append(f"{modifier} {seed}")
        for modifier in INTENT_MODIFIERS[KeywordIntent.TRANSACTIONAL][:2]:
            variants.append(f"{seed} {modifier}")

        entries: list[KeywordEntry] = []
        seen: set[str] = set()
        for keyword in variants:
            normalized = re.sub(r"\s+", " ", keyword.lower()).strip()
            if normalized in seen:
                continue
            seen.add(normalized)
            volume, difficulty, cpc = _estimate_metrics(seed, normalized)
            entries.append(
                KeywordEntry(
                    keyword=normalized,
                    volume=volume,
                    difficulty=difficulty,
                    intent=classify_intent(normalized),
                    cpc=cpc,
                )
            )
            if len(entries) >= limit:
                break

        entries.sort(key=lambda row: row.volume, reverse=True)
        return entries

    def cluster_keywords(self, keywords: list[KeywordEntry]) -> list[KeywordCluster]:
        buckets: dict[str, list[KeywordEntry]] = {}
        for entry in keywords:
            stem = _stem(entry.keyword)
            buckets.setdefault(stem, []).append(entry)

        clusters: list[KeywordCluster] = []
        for index, (stem, rows) in enumerate(sorted(buckets.items()), start=1):
            total_volume = sum(row.volume for row in rows)
            avg_difficulty = sum(row.difficulty for row in rows) / max(len(rows), 1)
            intent_counts: dict[str, int] = {}
            for row in rows:
                intent_counts[row.intent] = intent_counts.get(row.intent, 0) + 1
            dominant = max(intent_counts, key=intent_counts.get)
            clusters.append(
                KeywordCluster(
                    cluster_id=f"cluster-{index}",
                    theme=stem,
                    keywords=sorted(rows, key=lambda row: row.volume, reverse=True),
                    total_volume=total_volume,
                    avg_difficulty=avg_difficulty,
                    dominant_intent=dominant,
                )
            )
        clusters.sort(key=lambda row: row.total_volume, reverse=True)
        return clusters

    def gap_analysis(
        self,
        seed: str,
        our_keywords: list[str],
        competitor_keywords: list[str],
        *,
        limit: int = 10,
    ) -> GapAnalysisResult:
        our_set = {keyword.lower().strip() for keyword in our_keywords}
        competitor_set = {keyword.lower().strip() for keyword in competitor_keywords}

        missing_raw = sorted(competitor_set - our_set)[:limit]
        shared_raw = sorted(competitor_set & our_set)

        missing_entries = []
        for keyword in missing_raw:
            volume, difficulty, cpc = _estimate_metrics(seed, keyword)
            missing_entries.append(
                KeywordEntry(
                    keyword=keyword,
                    volume=volume,
                    difficulty=difficulty,
                    intent=classify_intent(keyword),
                    cpc=cpc,
                )
            )

        shared_entries = []
        for keyword in shared_raw[:limit]:
            volume, difficulty, cpc = _estimate_metrics(seed, keyword)
            shared_entries.append(
                KeywordEntry(
                    keyword=keyword,
                    volume=volume,
                    difficulty=difficulty,
                    intent=classify_intent(keyword),
                    cpc=cpc,
                )
            )

        opportunity = 0.0
        if missing_entries:
            opportunity = sum(entry.volume / max(entry.difficulty, 1) for entry in missing_entries) / len(missing_entries)

        return GapAnalysisResult(
            seed=seed,
            missing_keywords=missing_entries,
            shared_keywords=shared_entries,
            opportunity_score=opportunity,
        )
