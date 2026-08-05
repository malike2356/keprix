"""Benchmark and eval suite registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from keprix.compat import StrEnum
from typing import Any


class EvalCategory(StrEnum):
    CHAT_HELPFULNESS = "chat_helpfulness"
    TOOL_ROUTING = "tool_routing"
    TOOL_EXECUTION = "tool_execution"
    RESEARCH_SOURCE_QUALITY = "research_source_quality"
    CITATION_CORRECTNESS = "citation_correctness"
    DATA_ANALYSIS = "data_analysis"
    CODE_GENERATION = "code_generation"
    CYBER_SAFETY = "cyber_safety"
    LOCALIZATION = "localization"
    VOICE_TRANSCRIPTION = "voice_transcription"
    BILLING_ENTITLEMENT = "billing_entitlement"
    UI_CONTRACT = "ui_contract"


@dataclass
class EvalTask:
    id: str
    category: EvalCategory
    input: str
    description: str = ""
    expect_contains: str | None = None
    expect_blocked: bool = False
    citations_required: int | None = None
    max_cost_usd: float | None = None
    max_latency_ms: float | None = None
    tags: list[str] = field(default_factory=list)
    mock_output: str | None = None
    mock_blocked: bool | None = None
    mock_cost_usd: float | None = None
    mock_latency_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalSuite:
    name: str
    version: str
    category: EvalCategory
    tasks: list[EvalTask]
    min_pass_rate: float = 0.9
    source_path: str = ""


class EvalRegistry:
    """In-memory registry of loaded eval suites."""

    def __init__(self) -> None:
        self._suites: dict[str, EvalSuite] = {}

    def register(self, suite: EvalSuite) -> None:
        self._suites[suite.name] = suite

    def get(self, name: str) -> EvalSuite | None:
        return self._suites.get(name)

    def list_suites(self) -> list[str]:
        return sorted(self._suites.keys())

    def list_by_category(self, category: EvalCategory) -> list[EvalSuite]:
        return [suite for suite in self._suites.values() if suite.category == category]


eval_registry = EvalRegistry()
