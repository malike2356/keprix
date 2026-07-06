"""Benchmark and trace eval HTTP routes (Prompt 57)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from keprix.backend.evals.benchmark import get_benchmark_runner
from keprix.backend.evals.datasets import benchmark_registry, load_all_benchmarks
from keprix.backend.evals.regression import compare_to_baseline, load_baseline, save_baseline
from keprix.backend.evals.reports import build_report, failure_summary, render_json_report, render_markdown_report
from keprix.backend.observability.agent_trace import get_trace_store

router = APIRouter(prefix="/api/evals/benchmarks", tags=["eval-benchmarks"])


class BaselineRequest(BaseModel):
    baseline: dict[str, Any] = Field(default_factory=dict)


class RegressionRequest(BaseModel):
    min_pass_rate: float = Field(default=0.9, ge=0.0, le=1.0)
    baseline: dict[str, Any] | None = None


@router.get("/suites")
async def list_benchmark_suites(workflow: str | None = None) -> dict[str, Any]:
    load_all_benchmarks()
    if workflow:
        suites = [suite.name for suite in benchmark_registry.list_by_workflow(workflow)]
    else:
        suites = benchmark_registry.list_suites()
    return {"suites": suites, "workflows": sorted({s.workflow for s in benchmark_registry._suites.values()})}


@router.post("/run")
async def run_all_benchmarks() -> dict[str, Any]:
    runner = get_benchmark_runner(reload=True)
    results = await runner.run_all()
    report = build_report(results)
    return {
        "report": report.to_dict(),
        "suites": [result.to_dict() for result in results],
    }


@router.post("/run/{suite_name}")
async def run_benchmark_suite(suite_name: str) -> dict[str, Any]:
    runner = get_benchmark_runner(reload=True)
    try:
        result = await runner.run_suite(suite_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result.to_dict()


@router.post("/run/workflow/{workflow}")
async def run_workflow_benchmarks(workflow: str) -> dict[str, Any]:
    runner = get_benchmark_runner(reload=True)
    results = await runner.run_workflow(workflow)
    if not results:
        raise HTTPException(status_code=404, detail=f"No suites for workflow: {workflow}")
    report = build_report(results)
    return {
        "report": report.to_dict(),
        "suites": [result.to_dict() for result in results],
    }


@router.post("/report")
async def benchmark_report(body: RegressionRequest) -> dict[str, Any]:
    runner = get_benchmark_runner(reload=True)
    results = await runner.run_all()
    report = build_report(results, min_pass_rate=body.min_pass_rate)
    return {
        "report": report.to_dict(),
        "markdown": render_markdown_report(report, results),
        "json": render_json_report(report, results),
        "failures": failure_summary(report),
    }


@router.get("/baseline")
async def get_baseline() -> dict[str, Any]:
    return {"baseline": load_baseline()}


@router.post("/baseline")
async def set_baseline() -> dict[str, Any]:
    runner = get_benchmark_runner(reload=True)
    results = await runner.run_all()
    baseline = save_baseline(results)
    return {"baseline": baseline}


@router.post("/regression")
async def run_regression(body: RegressionRequest) -> dict[str, Any]:
    runner = get_benchmark_runner(reload=True)
    results = await runner.run_all()
    report = build_report(results, min_pass_rate=body.min_pass_rate)
    comparison = compare_to_baseline(results, body.baseline)
    return {
        "report": report.to_dict(),
        "regression": comparison.to_dict(),
        "failures": failure_summary(report),
    }


@router.get("/traces")
async def list_agent_traces(limit: int = 50) -> dict[str, Any]:
    store = get_trace_store()
    return {"traces": store.list_traces(limit=limit)}


@router.get("/traces/{run_id}")
async def get_agent_trace(run_id: str) -> dict[str, Any]:
    store = get_trace_store()
    trace = store.get(run_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace.to_dict(redact=True)
