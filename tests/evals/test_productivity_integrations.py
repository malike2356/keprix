"""Eval suite and HTTP wiring smoke for productivity integrations (prompt 176)."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.backend.evals.benchmark import BenchmarkRunner
from keprix.backend.evals.datasets import discover_benchmark_suites, load_all_benchmarks


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_productivity_suite_discovered():
    suites = discover_benchmark_suites()
    productivity = [suite for suite in suites if suite.workflow == "productivity"]
    assert productivity, "expected evals/suites/productivity/*.yaml"
    names = {suite.name for suite in productivity}
    assert "productivity_notion_trello" in names


@pytest.mark.asyncio
async def test_productivity_benchmark_runner_passes():
    registry = load_all_benchmarks()
    runner = BenchmarkRunner(registry)
    results = await runner.run_workflow("productivity")
    assert len(results) == 1
    result = results[0]
    assert result.suite == "productivity_notion_trello"
    assert result.passed == result.total
    assert result.pass_rate == 1.0


def test_catalog_has_notion_trello_keys():
    from keprix_cli.autonomous_mcp_catalog import get_catalog

    keys = {entry["key"] for entry in get_catalog()}
    assert {"notion", "notion-token", "trello"}.issubset(keys)


def test_rag_connectors_include_notion():
    from keprix.rag_pipeline.connectors.registry import list_connectors

    connector_ids = {item["id"] for item in list_connectors()}
    assert "notion" in connector_ids


def test_productivity_skills_present_on_disk():
    skills_root = PROJECT_ROOT / "src" / "keprix" / "skills" / "productivity"
    assert (skills_root / "trello" / "SKILL.md").is_file()
    assert (skills_root / "productivity-integrations" / "SKILL.md").is_file()


def test_example_playbook_parses():
    import yaml

    playbook = PROJECT_ROOT / "examples" / "productivity" / "notion-trello-sync" / "playbook.yaml"
    data = yaml.safe_load(playbook.read_text(encoding="utf-8"))
    assert data["name"] == "notion-trello-weekly-sync"
    assert len(data["steps"]) >= 2
