"""Mutation engine settings (Prompt 150)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class MutationSettings:
    enabled: bool
    tool_synthesis: bool
    prompt_evolution: bool
    self_coding: bool
    auto_approve_threshold: float
    synthesis_min_confidence: float
    require_tests: bool
    generated_tools_dir: str
    retention_days: int
    max_generated_tools: int
    prune_after_days: int
    repo_root: str
    branch_prefix: str
    merge_strategy: str


@lru_cache
def get_mutation_settings() -> MutationSettings:
    generated_dir = os.environ.get(
        "KEPRIX_MUTATION_GENERATED_TOOLS_DIR",
        os.environ.get("KEPRIX_GENERATED_TOOLS_DIR", os.path.expanduser("~/.keprix/generated/tools")),
    )
    return MutationSettings(
        enabled=_truthy(os.environ.get("KEPRIX_MUTATION_ENABLED"), default=True),
        tool_synthesis=_truthy(os.environ.get("KEPRIX_MUTATION_TOOL_SYNTHESIS"), default=True),
        prompt_evolution=_truthy(os.environ.get("KEPRIX_MUTATION_PROMPT_EVOLUTION"), default=False),
        self_coding=_truthy(os.environ.get("KEPRIX_MUTATION_SELF_CODING"), default=False),
        auto_approve_threshold=float(os.environ.get("KEPRIX_MUTATION_AUTO_APPROVE_THRESHOLD", "0.85")),
        synthesis_min_confidence=float(
            os.environ.get("KEPRIX_MUTATION_SYNTHESIS_MIN_CONFIDENCE", "0.75")
        ),
        require_tests=_truthy(os.environ.get("KEPRIX_MUTATION_REQUIRE_TESTS"), default=True),
        generated_tools_dir=generated_dir,
        retention_days=int(os.environ.get("KEPRIX_MUTATION_RETENTION_DAYS", "365")),
        max_generated_tools=int(os.environ.get("KEPRIX_MUTATION_MAX_GENERATED_TOOLS", "200")),
        prune_after_days=int(os.environ.get("KEPRIX_MUTATION_PRUNE_AFTER_DAYS", "90")),
        repo_root=os.environ.get("KEPRIX_MUTATION_REPO_ROOT", "."),
        branch_prefix=os.environ.get("KEPRIX_MUTATION_BRANCH_PREFIX", "mutation/"),
        merge_strategy=os.environ.get("KEPRIX_MUTATION_MERGE_STRATEGY", "squash"),
    )
