"""Load golden task suites from the repo evals/ tree."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from keprix.evals.registry import EvalCategory, EvalRegistry, EvalSuite, EvalTask, eval_registry


def find_evals_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "evals" / "golden_tasks"
        if candidate.is_dir():
            return parent / "evals"
    cwd_candidate = Path.cwd() / "evals" / "golden_tasks"
    if cwd_candidate.is_dir():
        return Path.cwd() / "evals"
    return here.parents[2] / "evals"


def _parse_category(raw: str) -> EvalCategory:
    try:
        return EvalCategory(raw)
    except ValueError:
        return EvalCategory.CHAT_HELPFULNESS


def _parse_task(raw: dict[str, Any], default_category: EvalCategory) -> EvalTask:
    category = _parse_category(str(raw.get("category") or default_category.value))
    return EvalTask(
        id=str(raw["id"]),
        category=category,
        input=str(raw.get("input") or ""),
        description=str(raw.get("description") or ""),
        expect_contains=raw.get("expect_contains"),
        expect_blocked=bool(raw.get("expect_blocked", False)),
        citations_required=raw.get("citations_required"),
        max_cost_usd=raw.get("max_cost_usd"),
        max_latency_ms=raw.get("max_latency_ms"),
        tags=list(raw.get("tags") or []),
        mock_output=raw.get("mock_output"),
        mock_blocked=raw.get("mock_blocked"),
        mock_cost_usd=raw.get("mock_cost_usd"),
        mock_latency_ms=raw.get("mock_latency_ms"),
        metadata=dict(raw.get("metadata") or {}),
    )


def load_suite_file(path: Path) -> EvalSuite:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    category = _parse_category(str(data.get("category") or "chat_helpfulness"))
    tasks = [_parse_task(item, category) for item in data.get("tasks") or []]
    return EvalSuite(
        name=str(data.get("name") or path.stem),
        version=str(data.get("version") or "1"),
        category=category,
        tasks=tasks,
        min_pass_rate=float(data.get("min_pass_rate", 0.9)),
        source_path=str(path),
    )


def discover_suites(root: Path | None = None) -> list[EvalSuite]:
    evals_root = root or find_evals_root()
    suites: list[EvalSuite] = []
    for subdir in ("golden_tasks", "research", "tools", "safety", "data_analysis"):
        directory = evals_root / subdir
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.yaml")):
            suites.append(load_suite_file(path))

    suites_dir = evals_root / "suites"
    if suites_dir.is_dir():
        for path in sorted(suites_dir.glob("**/*.yaml")):
            suites.append(load_suite_file(path))
    return suites


def load_all_into_registry(registry: EvalRegistry | None = None) -> EvalRegistry:
    target = registry or eval_registry
    for suite in discover_suites():
        target.register(suite)
    return target
