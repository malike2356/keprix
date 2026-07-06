"""Kernel plugin HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.api.auth import require_api_auth
from keprix.kernel.interoperability import get_interop_bridge
from keprix.kernel.memory_provider import get_memory_backend
from keprix.kernel.model_provider import get_model_provider_registry
from keprix.kernel.planner import KernelPlanner
from keprix.kernel.plugin_contract import KernelPlugin, get_plugin_registry
from keprix.kernel.function_contract import FunctionContract, InvocationKind, get_invocation_traces

router = APIRouter(prefix="/api/kernel", tags=["kernel"])


class InvokeBody(BaseModel):
    plugin: str
    function: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)


class PlanBody(BaseModel):
    goal: str = Field(..., min_length=1)
    permissions: list[str] = Field(default_factory=list)
    max_risk: str = "medium"
    required_output_type: str | None = None
    max_cost: int | None = None


class RegisterPluginBody(BaseModel):
    name: str
    version: str = "1.0.0"
    documentation: str = ""
    capability_tags: list[str] = Field(default_factory=list)
    functions: list[dict[str, Any]] = Field(default_factory=list)


class MemoryBody(BaseModel):
    key: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("/plugins")
async def list_plugins(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"plugins": get_plugin_registry().list_plugins()}


@router.get("/plugins/{plugin_name}")
async def inspect_plugin(plugin_name: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    plugin = get_plugin_registry().inspect(plugin_name)
    if plugin is None:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return plugin


@router.post("/plugins/register")
async def register_plugin(body: RegisterPluginBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    functions = [
        FunctionContract(
            name=str(item["name"]),
            description=str(item.get("description") or ""),
            input_schema=item.get("input_schema") or {"type": "object", "properties": {}},
            output_schema=item.get("output_schema") or {"type": "object"},
            invocation=InvocationKind(str(item.get("invocation") or InvocationKind.NATIVE.value)),
            risk_level=str(item.get("risk_level") or "low"),
            permissions=[str(value) for value in item.get("permissions") or []],
            cost_units=int(item.get("cost_units") or 1),
            output_type=str(item.get("output_type") or "text"),
        )
        for item in body.functions
    ]
    plugin = KernelPlugin(
        name=body.name,
        version=body.version,
        documentation=body.documentation,
        capability_tags=body.capability_tags,
        functions=functions,
    )
    get_plugin_registry().register(plugin)
    return plugin.to_dict()


@router.post("/invoke")
async def invoke_plugin(body: InvokeBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return get_plugin_registry().invoke(body.plugin, body.function, body.arguments, **body.context)


@router.post("/plan")
async def plan_goal(body: PlanBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    planner = KernelPlanner(get_plugin_registry())
    result = planner.plan(
        body.goal,
        permissions=set(body.permissions),
        max_risk=body.max_risk,
        required_output_type=body.required_output_type,
        max_cost=body.max_cost,
    )
    return result.to_dict()


@router.get("/traces")
async def list_traces(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"traces": get_invocation_traces()}


@router.get("/interop/mcp-tools")
async def list_mcp_tools(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"tools": get_interop_bridge().list_mcp_tools()}


@router.get("/interop/a2a-capabilities")
async def list_a2a_capabilities(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"agents": get_interop_bridge().list_a2a_capabilities()}


@router.get("/models")
async def list_model_providers(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"providers": get_model_provider_registry().list_providers()}


@router.post("/memory/remember")
async def remember_memory(body: MemoryBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    record_id = await get_memory_backend().remember(body.key, body.content, body.metadata)
    return {"id": record_id, "backend": get_memory_backend().name}


@router.get("/memory/recall")
async def recall_memory(query: str, limit: int = 5, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    rows = await get_memory_backend().recall(query, limit=limit)
    return {
        "backend": get_memory_backend().name,
        "results": [
            {"id": row.id, "key": row.key, "content": row.content, "metadata": row.metadata}
            for row in rows
        ],
    }
