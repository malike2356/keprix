"""Research depth presets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DepthConfig:
    sub_questions: int
    sources_per_question: int
    target_words: int


DEPTH_PRESETS: dict[str, DepthConfig] = {
    "quick": DepthConfig(sub_questions=5, sources_per_question=2, target_words=500),
    "standard": DepthConfig(sub_questions=8, sources_per_question=3, target_words=1500),
    "deep": DepthConfig(sub_questions=12, sources_per_question=5, target_words=3000),
}


def get_depth_config(depth: str) -> DepthConfig:
    return DEPTH_PRESETS.get(depth, DEPTH_PRESETS["standard"])
