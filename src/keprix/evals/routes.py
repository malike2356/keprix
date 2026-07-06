"""Eval harness HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from keprix.evals.datasets import load_all_into_registry
from keprix.evals.provider_compare import compare_providers
from keprix.evals.registry import eval_registry
from keprix.evals.reports import evaluate_release_gate, render_json_report
from keprix.evals.runner import get_runner
from keprix.evals.wiring import wiring_executor_for_suite

router = APIRouter(prefix="/api/evals", tags=["evals"])


class ReleaseGateRequest(BaseModel):
    min_pass_rate: float = Field(default=0.9, ge=0.0, le=1.0)
    baseline: dict[str, Any] = Field(default_factory=dict)


class ProviderCompareRequest(BaseModel):
    providers: dict[str, dict[str, Any]] = Field(default_factory=dict)


@router.get("/suites")
async def list_eval_suites() -> dict[str, Any]:
    load_all_into_registry()
    return {"suites": eval_registry.list_suites()}


@router.post("/run")
async def run_all_evals() -> dict[str, Any]:
    runner = get_runner(reload=True)
    results = []
    for suite_name in eval_registry.list_suites():
        executor = wiring_executor_for_suite(suite_name)
        results.append(await runner.run_suite(suite_name, executor=executor))
    gate = evaluate_release_gate(results)
    return {
        "release_gate": gate.to_dict(),
        "suites": [result.to_dict() for result in results],
    }


@router.post("/run/{suite_name}")
async def run_eval_suite(suite_name: str) -> dict[str, Any]:
    runner = get_runner(reload=True)
    executor = wiring_executor_for_suite(suite_name)
    try:
        result = await runner.run_suite(suite_name, executor=executor)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result.to_dict()


@router.post("/release-gate")
async def release_gate(body: ReleaseGateRequest) -> dict[str, Any]:
    runner = get_runner(reload=True)
    results = []
    for suite_name in eval_registry.list_suites():
        executor = wiring_executor_for_suite(suite_name)
        results.append(await runner.run_suite(suite_name, executor=executor))
    suites = [eval_registry.get(name) for name in eval_registry.list_suites()]
    gate = evaluate_release_gate(
        results,
        min_pass_rate=body.min_pass_rate,
        baseline=body.baseline,
        suites=[suite for suite in suites if suite is not None],
    )
    return {
        "release_gate": gate.to_dict(),
        "report_json": render_json_report(results, gate),
    }


@router.post("/compare")
async def compare_eval_providers(body: ProviderCompareRequest) -> dict[str, Any]:
    ranking = compare_providers(body.providers)
    return {
        "ranking": [
            {
                "provider": row.provider,
                "pass_rate": row.pass_rate,
                "avg_cost_usd": row.avg_cost_usd,
                "avg_latency_ms": row.avg_latency_ms,
                "rank": row.rank,
            }
            for row in ranking
        ]
    }


@router.get("/traces/{trace_id}")
async def get_eval_trace(trace_id: str) -> dict[str, Any]:
    from keprix.evals.trace_store import get_eval_trace_store

    record = get_eval_trace_store().get(trace_id)
    if record is None:
        store = get_eval_trace_store()
        from keprix.backend.observability.agent_trace import get_trace_store

        agent_trace = get_trace_store().get(trace_id)
        if agent_trace is not None:
            record = store.register(
                trace_id=trace_id,
                spans=[
                    {
                        "name": "agent",
                        "event": event_type,
                        "timestamp": agent_trace.started_at,
                        "payload": payload,
                    }
                    for event_type, payload in (
                        *[("node", item) for item in agent_trace.node_transitions],
                        *[("tool", item) for item in agent_trace.tool_calls],
                        *[("approval", item) for item in agent_trace.approvals],
                    )
                ],
                linked_run_ids={"agent": agent_trace.run_id},
                actual=agent_trace.user_request,
            )
    if record is None:
        raise HTTPException(status_code=404, detail="Eval trace not found")
    return record.to_dict()
