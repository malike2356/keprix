"""Load benchmark suites from evals/suites/ (Prompt 57)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from keprix.evals.registry import EvalCategory


@dataclass
class BenchmarkTask:
    id: str
    input: str
    description: str = ""
    expect_contains: str | None = None
    expect_blocked: bool = False
    citations_required: int | None = None
    required_artifacts: list[str] = field(default_factory=list)
    safety_expect_blocked: bool = False
    max_cost_usd: float | None = None
    max_runtime_ms: float | None = None
    graders: list[dict[str, Any]] = field(default_factory=list)
    mock_output: str | None = None
    mock_blocked: bool | None = None
    mock_cost_usd: float | None = None
    mock_latency_ms: float | None = None
    mock_artifacts: list[str] = field(default_factory=list)
    mock_tool_calls: list[dict[str, Any]] = field(default_factory=list)
    safety_critical: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    name: str
    version: str
    category: str
    workflow: str
    tasks: list[BenchmarkTask]
    min_pass_rate: float = 0.9
    max_cost_usd: float | None = None
    max_runtime_ms: float | None = None
    source_path: str = ""


def find_suites_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "evals" / "suites"
        if candidate.is_dir():
            return candidate
    cwd = Path.cwd() / "evals" / "suites"
    if cwd.is_dir():
        return cwd
    return here.parents[3] / "evals" / "suites"


def _default_graders(task: dict[str, Any]) -> list[dict[str, Any]]:
    graders: list[dict[str, Any]] = []
    meta = dict(task.get("metadata") or {})
    rubric = meta.get("rubric") or task.get("rubric")
    if rubric:
        graders.append({"type": "human_rubric", "items": list(rubric)})
    if task.get("expect_blocked") is not None or task.get("safety_expect_blocked"):
        graders.append(
            {
                "type": "safety_violation",
                "expect_blocked": bool(task.get("expect_blocked") or task.get("safety_expect_blocked")),
            }
        )
    if task.get("citations_required"):
        graders.append({"type": "citation_coverage", "min_citations": int(task["citations_required"])})
    required_artifacts = list(task.get("required_artifacts") or meta.get("required_artifacts") or [])
    if required_artifacts:
        graders.append({"type": "artifact_completeness", "required_artifacts": required_artifacts})
    if task.get("expect_contains"):
        graders.append({"type": "human_rubric", "items": [str(task["expect_contains"])]})
    if not graders:
        graders.append({"type": "human_rubric", "items": ["response"]})
    return graders


def _parse_task(raw: dict[str, Any]) -> BenchmarkTask:
    meta = dict(raw.get("metadata") or {})
    safety_critical = bool(raw.get("safety_critical") or meta.get("safety_critical"))
    graders = list(raw.get("graders") or _default_graders(raw))
    return BenchmarkTask(
        id=str(raw["id"]),
        input=str(raw.get("input") or ""),
        description=str(raw.get("description") or ""),
        expect_contains=raw.get("expect_contains"),
        expect_blocked=bool(raw.get("expect_blocked", False)),
        citations_required=raw.get("citations_required"),
        required_artifacts=list(raw.get("required_artifacts") or meta.get("required_artifacts") or []),
        safety_expect_blocked=bool(raw.get("safety_expect_blocked") or raw.get("expect_blocked", False)),
        max_cost_usd=raw.get("max_cost_usd"),
        max_runtime_ms=raw.get("max_runtime_ms") or raw.get("max_latency_ms"),
        graders=graders,
        mock_output=raw.get("mock_output"),
        mock_blocked=raw.get("mock_blocked"),
        mock_cost_usd=raw.get("mock_cost_usd"),
        mock_latency_ms=raw.get("mock_latency_ms"),
        mock_artifacts=list(raw.get("mock_artifacts") or []),
        mock_tool_calls=list(raw.get("mock_tool_calls") or []),
        safety_critical=safety_critical,
        metadata=meta,
    )


def load_suite_file(path: Path, workflow: str) -> BenchmarkSuite:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    tasks = [_parse_task(item) for item in data.get("tasks") or []]
    category = str(data.get("category") or EvalCategory.CHAT_HELPFULNESS.value)
    return BenchmarkSuite(
        name=str(data.get("name") or path.stem),
        version=str(data.get("version") or "1"),
        category=category,
        workflow=workflow,
        tasks=tasks,
        min_pass_rate=float(data.get("min_pass_rate", 0.9)),
        max_cost_usd=data.get("max_cost_usd"),
        max_runtime_ms=data.get("max_runtime_ms"),
        source_path=str(path),
    )


def discover_benchmark_suites(root: Path | None = None) -> list[BenchmarkSuite]:
    suites_root = root or find_suites_root()
    suites: list[BenchmarkSuite] = []
    if not suites_root.is_dir():
        return suites
    for workflow_dir in sorted(suites_root.iterdir()):
        if not workflow_dir.is_dir():
            continue
        for path in sorted(workflow_dir.glob("*.yaml")):
            suites.append(load_suite_file(path, workflow=workflow_dir.name))
    return suites


class BenchmarkRegistry:
    def __init__(self) -> None:
        self._suites: dict[str, BenchmarkSuite] = {}

    def register(self, suite: BenchmarkSuite) -> None:
        self._suites[suite.name] = suite

    def get(self, name: str) -> BenchmarkSuite | None:
        return self._suites.get(name)

    def list_suites(self) -> list[str]:
        return sorted(self._suites.keys())

    def list_by_workflow(self, workflow: str) -> list[BenchmarkSuite]:
        return [suite for suite in self._suites.values() if suite.workflow == workflow]


benchmark_registry = BenchmarkRegistry()


def load_all_benchmarks(registry: BenchmarkRegistry | None = None) -> BenchmarkRegistry:
    target = registry or benchmark_registry
    target._suites.clear()
    for suite in discover_benchmark_suites():
        target.register(suite)
    return target
