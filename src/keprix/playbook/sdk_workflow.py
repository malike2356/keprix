"""Compile SDK workflow specs into playbook graphs and start runs."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from keprix.playbook.runtime import (
    END,
    PlaybookGraph,
    PlaybookRunner,
    playbook_registry,
)
from keprix.playbook.runtime.errors import PlaybookGraphError
from keprix.playbook.runtime.interrupts import interrupt
from keprix.playbook.runtime.state import PlaybookRun


def _apply_patch(state: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(state)
    merged.update(patch)
    return merged


def _make_step_handler(step: dict[str, Any]):
    step_type = str(step.get("type") or "task")
    config = dict(step.get("config") or {})
    retry_cfg = step.get("retry") or {}
    max_attempts = int(retry_cfg.get("max_attempts") or 1)

    async def handler(state: dict[str, Any]) -> dict[str, Any]:
        attempt = 0
        last_error: Exception | None = None
        while attempt < max_attempts:
            attempt += 1
            try:
                return await _run_step(step_type, step, config, state)
            except Exception as exc:
                last_error = exc
                if attempt >= max_attempts:
                    raise
                await asyncio.sleep(float(retry_cfg.get("delay_seconds") or 0))
        if last_error:
            raise last_error
        return state

    return handler


async def _run_step(
    step_type: str,
    step: dict[str, Any],
    config: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    step_id = str(step.get("id") or "step")

    if step_type == "task":
        patch = dict(config.get("set") or {})
        if "value" in config and "key" in config:
            patch[str(config["key"])] = config["value"]
        if config.get("message"):
            patch[f"{step_id}_output"] = str(config["message"])
        return _apply_patch(state, patch)

    if step_type == "branch":
        key = str(config.get("key") or "")
        expected = config.get("equals")
        actual = state.get(key)
        branch = "true" if actual == expected else "false"
        return _apply_patch(state, {f"{step_id}_branch": branch})

    if step_type == "parallel":
        tasks = list(config.get("tasks") or [])
        results: dict[str, Any] = {}
        for index, task in enumerate(tasks):
            task_id = str(task.get("id") or f"task-{index}")
            patch = dict(task.get("set") or {})
            if "value" in task:
                patch[task_id] = task["value"]
            results[task_id] = patch
        merged = dict(state)
        merged[f"{step_id}_parallel"] = results
        for patch in results.values():
            if isinstance(patch, dict):
                merged.update(patch)
        return merged

    if step_type == "approval":
        if not state.get(f"{step_id}_approved"):
            interrupt(
                str(config.get("message") or "Human approval required"),
                approval_request={
                    "step_id": step_id,
                    "risk": config.get("risk") or "medium",
                    "summary": config.get("summary") or step_id,
                },
            )
        return _apply_patch(state, {f"{step_id}_approved": True})

    if step_type == "artifact":
        artifact = {
            "name": str(config.get("name") or step_id),
            "content": config.get("content") or state.get(str(config.get("from_key") or "")),
            "step_id": step_id,
        }
        artifacts = list(state.get("_artifacts") or [])
        artifacts.append(artifact)
        return _apply_patch(state, {"_artifacts": artifacts})

    if step_type == "crew_execute":
        from keprix.playbook.crew_nodes import crew_execute_node

        team_id = str(config.get("team_id") or config.get("name") or "")
        objective = config.get("objective")
        if objective is None:
            objective = state.get("objective")
        return await crew_execute_node(
            state,
            team_id=team_id,
            objective=str(objective) if objective is not None else None,
        )

    if step_type == "browser_action":
        from keprix.playbook.browser_nodes import browser_action_node

        return await browser_action_node(
            state,
            skill=str(config.get("skill") or ""),
            objective=config.get("objective") if config.get("objective") is not None else state.get("objective"),
            workspace_id=str(config.get("workspace_id") or state.get("workspace_id") or "default"),
            profile_kind=str(config.get("profile_kind") or "disposable"),
            approved=bool(config.get("approved", True)),
            url=str(config.get("url") or "about:blank"),
        )

    if step_type == "analytics_ingest":
        from keprix.playbook.analytics_nodes import analytics_ingest_node

        data = config.get("data")
        if data is None:
            data = state.get("analytics_data")
        return await analytics_ingest_node(
            state,
            dataset_name=str(config.get("dataset_name") or "main"),
            data=str(data) if data is not None else None,
        )

    if step_type == "analytics_code":
        from keprix.playbook.analytics_nodes import analytics_code_node

        code = config.get("code")
        if code is None:
            code = state.get("analytics_code")
        return await analytics_code_node(
            state,
            code=str(code) if code is not None else None,
            dataset_name=config.get("dataset_name"),
        )

    if step_type == "self_coding_job":
        from keprix.playbook.self_coding_nodes import self_coding_job_node

        instruction = config.get("instruction")
        if instruction is None:
            instruction = state.get("instruction") or state.get("objective")
        return await self_coding_job_node(
            state,
            project_id=str(config.get("project_id") or ""),
            instruction=str(instruction) if instruction is not None else None,
        )

    raise PlaybookGraphError(f"Unsupported workflow step type '{step_type}'")


def compile_workflow_spec(spec: dict[str, Any]) -> PlaybookGraph:
    graph_id = str(spec.get("graph_id") or "sdk-workflow")
    steps = list(spec.get("steps") or [])
    edges = list(spec.get("edges") or [])
    if not steps:
        raise PlaybookGraphError("Workflow spec requires at least one step")

    graph = PlaybookGraph(graph_id)
    step_ids = {str(step["id"]) for step in steps if step.get("id")}

    for step in steps:
        step_id = str(step.get("id") or "")
        if not step_id:
            raise PlaybookGraphError("Each step requires an id")
        graph.add_node(step_id, _make_step_handler(step))

    if edges:
        for edge in edges:
            source = str(edge.get("from") or edge.get("source") or "")
            target = str(edge.get("to") or edge.get("target") or END)
            if source not in step_ids:
                raise PlaybookGraphError(f"Unknown edge source '{source}'")
            if target not in step_ids and target != END:
                raise PlaybookGraphError(f"Unknown edge target '{target}'")
            condition = None
            if edge.get("when") is not None:
                when = str(edge["when"])
                branch_source = source

                def _condition(state: dict[str, Any], w: str = when, sid: str = branch_source) -> bool:
                    return state.get(f"{sid}_branch") == w

                condition = _condition
            graph.add_edge(source, target, condition=condition)
    else:
        ordered = [str(step["id"]) for step in steps]
        for index, step_id in enumerate(ordered):
            target = ordered[index + 1] if index + 1 < len(ordered) else END
            graph.add_edge(step_id, target)

    entry = spec.get("entry")
    if entry:
        graph.set_entry(str(entry))
    return graph


async def start_workflow_run(
    spec: dict[str, Any],
    *,
    workspace_id: str,
    initial_state: dict[str, Any] | None = None,
) -> PlaybookRun:
    graph = compile_workflow_spec(spec).compile()
    runner = PlaybookRunner(graph)
    trace_id = str(uuid.uuid4())
    merged_state = dict(initial_state or {})
    merged_state["trace_id"] = trace_id
    run = await runner.start(workspace_id=workspace_id, initial_state=merged_state)
    artifacts = run.state.pop("_artifacts", None)
    if isinstance(artifacts, list):
        run.artifacts.extend(artifacts)
    playbook_registry.register(run, runner)
    from keprix.evals.trace_store import register_playbook_trace

    register_playbook_trace(
        trace_id=trace_id,
        playbook_run_id=run.run_id,
        graph_id=str(spec.get("graph_id") or graph.graph_id),
        status=run.status.value,
        workspace_id=workspace_id,
    )
    run.state["trace_id"] = trace_id
    return run
