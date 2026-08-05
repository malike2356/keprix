"""Load and match against the Keprix capability registry."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

REGISTRY_PATH = Path(__file__).resolve().parent / "capability_registry.yaml"


@lru_cache(maxsize=1)
def _raw_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return {"capabilities": {}, "aliases": {}}
    payload = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    return {
        "capabilities": dict(payload.get("capabilities") or {}),
        "aliases": dict(payload.get("aliases") or {}),
    }


def load_capability_map() -> dict[str, str]:
    """Return capability_id -> description for inventory equivalence matching."""
    return dict(_raw_registry()["capabilities"])


def _tokenize(text: str) -> set[str]:
    words: set[str] = set()
    for token in text.lower().split():
        cleaned = "".join(ch for ch in token if ch.isalnum())
        if len(cleaned) > 2:
            words.add(cleaned)
    return words


def match_capability(feature_text: str, *, threshold: float = 0.35) -> tuple[str | None, float]:
    """Return best matching capability id and score for a Hermes feature description.

    Alias hits are soft hints only. Strong ``already_have`` decisions should require
    score >= 0.5 from description overlap against capability text.
    """
    registry = _raw_registry()
    feature_words = _tokenize(feature_text)
    if not feature_words:
        return None, 0.0

    alias_hits: set[str] = set()
    for alias, cap_id in registry["aliases"].items():
        if alias in feature_words and cap_id in registry["capabilities"]:
            alias_hits.add(cap_id)

    best_id: str | None = None
    best_score = 0.0
    for cap_id, description in registry["capabilities"].items():
        existing_words = _tokenize(f"{cap_id.replace('-', ' ')} {description}")
        if not existing_words:
            continue
        overlap = feature_words & existing_words
        score = len(overlap) / max(len(feature_words), 1)
        if cap_id in alias_hits:
            score = min(1.0, score + 0.15)
        if score > best_score:
            best_score = score
            best_id = cap_id

    if best_id is None and alias_hits:
        # Alias-only hint: return a soft match below already_have threshold.
        return next(iter(alias_hits)), 0.4

    if best_score >= threshold:
        return best_id, best_score
    if alias_hits:
        return next(iter(alias_hits)), 0.4
    return None, best_score


def clear_registry_cache() -> None:
    _raw_registry.cache_clear()
