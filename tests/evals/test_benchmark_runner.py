"""Benchmark runner tests (Prompt 57)."""

from __future__ import annotations

import pytest

from keprix.backend.evals.benchmark import BenchmarkRunner
from keprix.backend.evals.datasets import load_all_benchmarks
from keprix.backend.evals.regression import compare_to_baseline, save_baseline
from keprix.backend.evals.reports import build_report, render_markdown_report


@pytest.fixture
def runner():
    registry = load_all_benchmarks()
    return BenchmarkRunner(registry)


@pytest.mark.asyncio
async def test_benchmark_runner_executes_starter_suites(runner):
    results = await runner.run_all()
    assert len(results) >= 6
    assert all(result.pass_rate == 1.0 for result in results)


@pytest.mark.asyncio
async def test_workflow_benchmarks(runner):
    results = await runner.run_workflow("research")
    assert len(results) == 1
    assert results[0].suite == "research_basics"
    assert results[0].passed == results[0].total


@pytest.mark.asyncio
async def test_report_includes_cost_and_safety(runner):
    results = await runner.run_all()
    report = build_report(results)
    assert report.metrics.avg_cost_usd >= 0.0
    assert "pass_rate" in report.to_dict()
    markdown = render_markdown_report(report, results)
    assert "Benchmark Report" in markdown


@pytest.mark.asyncio
async def test_baseline_comparison(runner, tmp_path):
    results = await runner.run_all()
    baseline = save_baseline(results, path=tmp_path / "baseline.json")
    comparison = compare_to_baseline(results, baseline)
    assert comparison.passed is True
    assert comparison.pass_rate_delta == pytest.approx(0.0)
