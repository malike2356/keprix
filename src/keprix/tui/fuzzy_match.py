"""Fuzzy matching helpers for commands, skills, models, and history."""

from __future__ import annotations


def fuzzy_score(query: str, candidate: str) -> int | None:
    query = query.lower().strip()
    candidate = candidate.lower()
    if not query:
        return 0
    score = 0
    pos = 0
    for char in query:
        found = candidate.find(char, pos)
        if found < 0:
            return None
        score += found - pos
        pos = found + 1
    return score


def fuzzy_filter(query: str, candidates: list[str], *, limit: int = 20) -> list[str]:
    scored = [(score, candidate) for candidate in candidates if (score := fuzzy_score(query, candidate)) is not None]
    return [candidate for _, candidate in sorted(scored, key=lambda item: (item[0], item[1]))[:limit]]

