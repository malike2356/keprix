"""HTTP routes for typed agent schema export and runs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.public_api.auth import require_developer_session
from keprix.typed_agents.agent import AgentRunResult
from keprix.typed_agents.deps_factory import build_support_dependencies
from keprix.typed_agents.registry import bootstrap_typed_agents, get_typed_agent, list_typed_agents
from keprix.typed_agents.schemas import AgentRunContext

router = APIRouter(prefix="/api/typed-agents", tags=["typed-agents"])


class TypedAgentRunBody(BaseModel):
    workspace_id: str = "default"
    user_id: str | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    raw_output: dict[str, Any] = Field(default_factory=dict)
    auto_approve: bool = False


@router.get("")
async def list_agents(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    bootstrap_typed_agents()
    names = list_typed_agents()
    inventory: list[dict[str, Any]] = []
    for name in names:
        agent = get_typed_agent(name)
        if agent is None:
            continue
        tools = list(agent.tools.values())
        inventory.append(
            {
                "name": name,
                "tool_count": len(tools),
                "tools": [tool.name for tool in tools],
                "approval_gated_tools": sum(1 for tool in tools if tool.approval_action),
                "output_schema": getattr(agent.output_type, "__name__", "output"),
                "deps_schema": getattr(agent.deps_type, "__name__", "deps"),
            }
        )
    return {"agents": names, "inventory": inventory, "count": len(names)}


@router.get("/{name}/schemas")
async def export_schemas(name: str, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    bootstrap_typed_agents()
    agent = get_typed_agent(name)
    if agent is None:
        raise HTTPException(status_code=404, detail="Typed agent not found")
    context = AgentRunContext(workspace_id="default", user_id="sdk")
    return agent.export_schemas(context)


@router.post("/{name}/run")
async def run_typed_agent(
    name: str,
    body: TypedAgentRunBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    bootstrap_typed_agents()
    agent = get_typed_agent(name)
    if agent is None:
        raise HTTPException(status_code=404, detail="Typed agent not found")

    user_id = body.user_id or str(user.get("id") or user.get("username") or "default")
    deps = await build_support_dependencies(workspace_id=body.workspace_id, user_id=user_id)
    context = AgentRunContext(workspace_id=body.workspace_id, user_id=user_id)
    try:
        result: AgentRunResult[Any] = await agent.run(
            deps=deps,
            context=context,
            tool_calls=body.tool_calls,
            raw_output=body.raw_output,
            auto_approve=body.auto_approve,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result.to_dict()
