"""Reference adoption release smoke orchestration (Prompt 59)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keprix.analytics.code_interpreter import CodeInterpreter
from keprix.analytics.container_executor import ContainerExecutor
from keprix.playbook.runtime import END
from keprix.playbook.runtime.runner import PlaybookRunner
from keprix.playbook.sdk_workflow import start_workflow_run
from keprix.rag_pipeline.component import PipelineContext
from keprix.rag_pipeline.evaluator import PipelineEvaluator
from keprix.teams.yaml_loader import crew_from_yaml

ADOPTION_SMOKE_YAML = """
name: adoption-smoke-crew
roles:
  coordinator:
    goal: Coordinate adoption smoke
    backstory: Release engineer
  reviewer:
    goal: Review outputs
    backstory: QA reviewer
tasks:
  coordinate:
    description: Run adoption smoke coordination task
    role: coordinator
    allow_delegation: true
    expected_output: smoke.md
flow:
  start: coordinate
"""


async def run_reference_adoption_smoke(
    *,
    workspace_id: str = "adoption-smoke",
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Run playbook, crew, browser, analytics, and eval surfaces in one fixture."""
    playbook_run = await start_workflow_run(
        {
            "graph_id": "reference-adoption-smoke",
            "entry": "bootstrap",
            "steps": [
                {
                    "id": "bootstrap",
                    "type": "task",
                    "config": {"key": "phase", "value": "adoption-smoke"},
                },
                {
                    "id": "browser",
                    "type": "browser_action",
                    "config": {
                        "skill": "checkout_dry_run",
                        "objective": "adoption browser dry run",
                        "workspace_id": workspace_id,
                        "profile_kind": "disposable",
                        "approved": True,
                    },
                },
                {
                    "id": "record",
                    "type": "artifact",
                    "config": {"name": "adoption-smoke", "from_key": "phase"},
                },
            ],
            "edges": [
                {"from": "bootstrap", "to": "browser"},
                {"from": "browser", "to": "record"},
                {"from": "record", "to": END},
            ],
        },
        workspace_id=workspace_id,
        initial_state={"workspace_id": workspace_id},
    )

    crew, flow = crew_from_yaml(ADOPTION_SMOKE_YAML)
    compiled = flow.compile_to_playbook(crew).compile()
    crew_run = await PlaybookRunner(compiled).execute_inline({"objective": "Adoption smoke crew"})
    crew_state = crew_run.state

    browser_payload = playbook_run.state.get("browser_result") or {}
    browser_result = browser_payload.get("result") or browser_payload

    interpreter = CodeInterpreter(executor=ContainerExecutor(container_required=False))
    analytics_session = interpreter.create_session()
    verification, analytics_result = interpreter.run_code(
        analytics_session,
        "print('analytics-dry-run')\n",
    )

    eval_ctx = PipelineContext(
        user_id="adoption-smoke",
        query="adoption smoke eval",
        answer="Adoption smoke completed with citations.",
        citations=[{"snippet": "Adoption smoke completed", "source_id": "smoke-doc"}],
        ranked=[{"content": "adoption smoke eval trace", "score": 0.9}],
        confidence=0.85,
        route="direct_answer",
    )
    eval_report = PipelineEvaluator().evaluate_run(eval_ctx, pipeline_id="reference-adoption-smoke")

    browser_session_id = str(browser_payload.get("session_id") or "")
    from keprix.evals.trace_store import register_adoption_smoke_trace

    register_adoption_smoke_trace(
        trace_id=eval_report.eval_id,
        playbook_run_id=playbook_run.run_id,
        crew_name=crew.name,
        browser_session_id=browser_session_id or None,
        analytics_session_id=analytics_session.session_id,
        eval_id=eval_report.eval_id,
    )

    return {
        "playbook_run_id": playbook_run.run_id,
        "playbook_status": playbook_run.status.value,
        "trace_id": eval_report.eval_id,
        "crew": {
            "name": crew.name,
            "task_results": crew_state.get("task_results", {}),
        },
        "browser": browser_result,
        "analytics": {
            "session_id": analytics_session.session_id,
            "ok": analytics_result.ok,
            "verification_allowed": verification.allowed,
            "stdout": analytics_result.stdout,
        },
        "eval": eval_report.to_dict(),
        "repo_root": str(repo_root or Path.cwd()),
    }
