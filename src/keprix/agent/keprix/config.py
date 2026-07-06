"""Mutation engine configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _truthy(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class MutationConfig:
    enabled: bool
    sandbox_timeout_s: int
    gap_confidence: float
    admin_channel: str
    max_retries: int
    require_approval: bool
    generated_tools_dir: str
    generated_skills_dir: str
    required_approval_channels: frozenset[str]


def _channels_from_env() -> frozenset[str]:
    raw = os.environ.get("KEPRIX_MUTATION_REQUIRED_CHANNELS", "web_ui,telegram")
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def get_mutation_config() -> MutationConfig:
    return MutationConfig(
        enabled=_truthy(os.environ.get("KEPRIX_MUTATION_ENABLED"), default=True),
        sandbox_timeout_s=int(os.environ.get("KEPRIX_SANDBOX_TIMEOUT", "30")),
        gap_confidence=float(os.environ.get("KEPRIX_GAP_CONFIDENCE", "0.7")),
        admin_channel=os.environ.get("KEPRIX_MUTATION_ADMIN_CHANNEL", "web"),
        max_retries=int(os.environ.get("KEPRIX_MUTATION_MAX_RETRIES", "2")),
        require_approval=_truthy(os.environ.get("KEPRIX_MUTATION_REQUIRE_APPROVAL"), default=True),
        generated_tools_dir=os.environ.get(
            "KEPRIX_GENERATED_TOOLS_DIR",
            os.path.expanduser("~/.keprix/generated/tools"),
        ),
        generated_skills_dir=os.environ.get(
            "KEPRIX_GENERATED_SKILLS_DIR",
            os.path.expanduser("~/.keprix/generated/skills"),
        ),
        required_approval_channels=_channels_from_env(),
    )
