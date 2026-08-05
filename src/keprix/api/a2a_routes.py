"""A2A agent registry and task management API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.providers.a2a.agent_discovery import AgentCard
from keprix.providers.a2a.runtime import ensure_default_agents, get_agent_registry, get_task_manager
from keprix.providers.a2a.task_manager import TaskStatus

router = APIRouter(prefix="/api/a2a", tags=["a2a"])


class RegisterAgentBody(BaseModel):
    id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    capabilities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    endpoint: str = Field(default="", max_length=500)


class CreateTaskBody(BaseModel):
    description: str = Field(..., min_length=1, max_length=4000)
    agent_id: str = Field(default="", max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("/status")
async def a2a_status(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    registry = await ensure_default_agents()
    manager = get_task_manager()
    agents = await registry.all()
    tasks = await manager.all()
    by_status: dict[str, int] = {}
    for task in tasks:
        by_status[task.status.value] = by_status.get(task.status.value, 0) + 1
    return {
        "enabled": True,
        "agent_count": len(agents),
        "task_count": len(tasks),
        "tasks_by_status": by_status,
    }


@router.get("/agents")
async def list_agents(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    registry = await ensure_default_agents()
    agents = await registry.all()
    return {"agents": [agent.to_dict() for agent in agents]}


@router.post("/agents")
async def register_agent(body: RegisterAgentBody, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    registry = await ensure_default_agents()
    card = AgentCard(
        id=body.id.strip(),
        name=body.name.strip(),
        description=body.description.strip(),
        capabilities=[item.strip() for item in body.capabilities if item.strip()],
        tags=[item.strip() for item in body.tags if item.strip()],
        endpoint=body.endpoint.strip(),
    )
    await registry.register(card)
    return {"agent": card.to_dict()}


@router.delete("/agents/{agent_id}")
async def unregister_agent(agent_id: str, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    registry = get_agent_registry()
    if agent_id == "keprix-local":
        raise HTTPException(status_code=400, detail="Cannot remove the built-in local agent")
    existing = await registry.get(agent_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await registry.unregister(agent_id)
    return {"ok": True, "id": agent_id}


@router.get("/tasks")
async def list_tasks(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    await ensure_default_agents()
    tasks = await get_task_manager().all()
    tasks_sorted = sorted(tasks, key=lambda row: row.updated_at, reverse=True)
    return {"tasks": [task.to_dict() for task in tasks_sorted]}


@router.post("/tasks")
async def create_task(body: CreateTaskBody, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    registry = await ensure_default_agents()
    manager = get_task_manager()
    agent_id = body.agent_id.strip()
    if agent_id:
        agent = await registry.get(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
    task = await manager.create(body.description.strip(), metadata=body.metadata)
    if agent_id:
        await manager.start(task.id, agent_id=agent_id)
        task = await manager.get(task.id)
    return {"task": task.to_dict() if task else None}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    task = await get_task_manager().get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": task.to_dict(), "artifacts": [
        {
            "type": artifact.type,
            "content": artifact.content,
            "step": artifact.step,
            "created_at": artifact.created_at,
        }
        for artifact in task.artifacts
    ]}


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    manager = get_task_manager()
    task = await manager.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.STREAMING):
        raise HTTPException(status_code=400, detail=f"Cannot cancel task in status {task.status.value}")
    await manager.cancel(task_id)
    updated = await manager.get(task_id)
    return {"task": updated.to_dict() if updated else None}
