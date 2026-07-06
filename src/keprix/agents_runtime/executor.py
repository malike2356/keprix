"""High-level agent run orchestration."""

from __future__ import annotations

from typing import Any

from keprix.agents_runtime.agent_spec import AgentSpec, get_agent
from keprix.agents_runtime.guardrail import run_guardrails
from keprix.agents_runtime.handoff import execute_handoff
from keprix.agents_runtime.run_context import RunContext, get_run, save_run


async def run_agent_step(
    ctx: RunContext,
    *,
    user_input: str,
    draft_output: str | None = None,
) -> dict[str, Any]:
    spec = get_agent(ctx.current_agent)
    if spec is None:
        return {"status": "error", "message": f"Unknown agent: {ctx.current_agent}"}

    input_result = run_guardrails(user_input, spec, phase="input", context=ctx.state)
    if not input_result.passed:
        ctx.record("guardrail", ctx.current_agent, input_result.__dict__)
        return {"status": "blocked", "phase": "input", **input_result.__dict__}

    output = draft_output or f"{spec.name} processed: {user_input}"
    output_result = run_guardrails(output, spec, phase="output", context=ctx.state)
    if not output_result.passed:
        ctx.record("guardrail", ctx.current_agent, output_result.__dict__)
        return {"status": "repair", "phase": "output", **output_result.__dict__}

    ctx.record("output", ctx.current_agent, {"text": output})
    ctx.state["last_output"] = output
    ctx.record("agent_end", ctx.current_agent, {})
    save_run(ctx)
    return {"status": "ok", "output": output, "agent": ctx.current_agent}


async def start_run(agent_name: str, *, user_input: str, state: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = RunContext.start(agent_name, initial_state=state)
    save_run(ctx)
    result = await run_agent_step(ctx, user_input=user_input)
    return {"run_id": ctx.run_id, **result}


async def handoff_run(
    run_id: str,
    *,
    target: str,
    reason: str,
    handoff_type: str = "agent",
    accept: bool = True,
) -> dict[str, Any]:
    ctx = get_run(run_id)
    if ctx is None:
        return {"status": "error", "message": "Run not found"}
    record = execute_handoff(
        ctx,
        target=target,
        reason=reason,
        handoff_type=handoff_type,  # type: ignore[arg-type]
        accepted=accept,
    )
    save_run(ctx)
    return {"status": "ok", "handoff": record.to_dict(), "current_agent": ctx.current_agent}
