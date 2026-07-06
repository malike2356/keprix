"""Multi-agent HTTP routes (Prompt 58)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from keprix.backend.multiagent.agent_tool import AgentTool
from keprix.backend.multiagent.group_chat import GroupChat, GroupChatPolicy
from keprix.backend.multiagent.message import AgentMessage, MessageType
from keprix.backend.multiagent.registry import MultiAgentPlaybook, default_playbook, get_agent_registry
from keprix.backend.multiagent.runtime import clear_messages, get_messages, get_run_events, send_message
from keprix.backend.multiagent.stream import get_run_stream
from keprix.backend.multiagent.workbench import McpServerConfig, get_mcp_workbench

router = APIRouter(prefix="/api/multiagent", tags=["multiagent"])


class SendMessageBody(BaseModel):
    sender: str
    recipient: str
    workspace_id: str = "local"
    run_id: str | None = None
    content: str
    message_type: str = MessageType.AGENT.value
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentToolBody(BaseModel):
    input: str
    workspace_id: str = "local"
    run_id: str | None = None
    caller: str = "coordinator"


class GroupChatBody(BaseModel):
    content: str
    participants: list[str]
    supervisor: str
    policy: str = GroupChatPolicy.ROUND_ROBIN.value
    workspace_id: str = "local"
    run_id: str | None = None


class PlaybookSaveBody(BaseModel):
    name: str
    workspace_id: str = "local"
    roles: dict[str, dict[str, Any]] = Field(default_factory=dict)
    connections: list[dict[str, str]] = Field(default_factory=list)
    group_chat: dict[str, Any] = Field(default_factory=dict)
    mcp_servers: list[dict[str, Any]] = Field(default_factory=list)


class McpBindBody(BaseModel):
    agent_id: str
    server: str
    tools: list[str] = Field(default_factory=list)


class McpInvokeBody(BaseModel):
    agent_id: str
    server: str
    tool_name: str
    params: dict[str, Any] = Field(default_factory=dict)
    workspace_id: str = "local"
    run_id: str | None = None
    approved: bool = False


class DryRunBody(BaseModel):
    playbook_name: str
    input: str = "Dry run coordination task"


@router.get("/roles")
async def list_roles() -> dict[str, Any]:
    registry = get_agent_registry()
    return {
        "roles": [
            {"name": name, **(registry.get_role(name).to_dict() if registry.get_role(name) else {})}
            for name in registry.list_roles()
        ]
    }


@router.post("/messages")
async def post_message(body: SendMessageBody) -> dict[str, Any]:
    run_id = body.run_id or str(uuid4())
    message = await send_message(
        AgentMessage(
            sender=body.sender,
            recipient=body.recipient,
            workspace_id=body.workspace_id,
            run_id=run_id,
            content=body.content,
            message_type=MessageType(body.message_type),
            metadata=body.metadata,
        )
    )
    get_run_stream(run_id).log(f"{body.sender} -> {body.recipient}: {body.content[:120]}")
    return message.to_dict()


@router.get("/messages")
async def list_messages(
    workspace_id: str | None = None,
    run_id: str | None = None,
    sender: str | None = None,
    recipient: str | None = None,
) -> dict[str, Any]:
    messages = get_messages(
        workspace_id=workspace_id,
        run_id=run_id,
        sender=sender,
        recipient=recipient,
    )
    return {"messages": [message.to_dict() for message in messages]}


@router.post("/agent-tools/{agent_id}/call")
async def call_agent_tool(agent_id: str, body: AgentToolBody) -> dict[str, Any]:
    run_id = body.run_id or str(uuid4())
    stream = get_run_stream(run_id)
    stream.log(f"Calling agent tool {agent_id}", agent=body.caller)
    try:
        tool = AgentTool(agent_id, workspace_id=body.workspace_id, run_id=run_id, caller=body.caller)
        result = await tool.call(body.input)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    stream.log(result.output, agent=agent_id)
    return result.to_dict()


@router.post("/group-chat")
async def run_group_chat(body: GroupChatBody) -> dict[str, Any]:
    run_id = body.run_id or str(uuid4())
    try:
        policy = GroupChatPolicy(body.policy)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Unknown policy: {body.policy}") from exc
    chat = GroupChat(
        participants=body.participants,
        supervisor=body.supervisor,
        policy=policy,
        workspace_id=body.workspace_id,
        run_id=run_id,
    )
    messages = await chat.dispatch(body.content)
    stream = get_run_stream(run_id)
    stream.log(f"Group chat ({policy.value}) dispatched to {len(messages)} recipients")
    return {
        "run_id": run_id,
        "policy": policy.value,
        "messages": [message.to_dict() for message in messages],
    }


@router.get("/workbench/tools")
async def list_workbench_tools(server: str | None = None) -> dict[str, Any]:
    workbench = get_mcp_workbench()
    return {"tools": workbench.list_tools(server=server)}


@router.post("/workbench/servers")
async def register_workbench_server(name: str, trusted: bool = True) -> dict[str, Any]:
    workbench = get_mcp_workbench()
    workbench.register_server(McpServerConfig(name=name, trusted=trusted))
    return {"server": name, "trusted": trusted}


@router.post("/workbench/bind")
async def bind_workbench_tools(body: McpBindBody) -> dict[str, Any]:
    workbench = get_mcp_workbench()
    try:
        return workbench.bind_tools(body.agent_id, body.tools, server=body.server)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/workbench/invoke")
async def invoke_workbench_tool(body: McpInvokeBody) -> dict[str, Any]:
    run_id = body.run_id or str(uuid4())
    workbench = get_mcp_workbench()
    try:
        result = await workbench.invoke_tool(
            agent_id=body.agent_id,
            server=body.server,
            tool_name=body.tool_name,
            params=body.params,
            workspace_id=body.workspace_id,
            run_id=run_id,
            approved=body.approved,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result


@router.post("/playbooks")
async def save_playbook(body: PlaybookSaveBody) -> dict[str, Any]:
    from keprix.backend.multiagent.registry import AgentRoleDef

    registry = get_agent_registry()
    roles = {
        role_id: AgentRoleDef(
            name=role_id,
            goal=str(config.get("goal") or ""),
            backstory=str(config.get("backstory") or ""),
            tools=list(config.get("tools") or []),
            connects_to=list(config.get("connects_to") or []),
        )
        for role_id, config in body.roles.items()
    }
    playbook = MultiAgentPlaybook(
        name=body.name,
        workspace_id=body.workspace_id,
        roles=roles,
        connections=body.connections,
        group_chat=body.group_chat,
        mcp_servers=body.mcp_servers,
    )
    path = registry.save_playbook(playbook)
    return {"name": playbook.name, "path": str(path), "yaml": playbook.to_yaml()}


@router.get("/playbooks")
async def list_playbooks() -> dict[str, Any]:
    registry = get_agent_registry()
    registry.load_playbooks_from_disk()
    return {"playbooks": registry.list_playbooks()}


@router.get("/playbooks/{name}")
async def get_playbook(name: str) -> dict[str, Any]:
    registry = get_agent_registry()
    registry.load_playbooks_from_disk()
    playbook = registry.get_playbook(name)
    if playbook is None and name == "starter-team":
        playbook = default_playbook()
    if playbook is None:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return {"name": playbook.name, "yaml": playbook.to_yaml(), "roles": list(playbook.roles.keys())}


@router.post("/playbooks/dry-run")
async def dry_run_playbook(body: DryRunBody) -> dict[str, Any]:
    registry = get_agent_registry()
    playbook = registry.get_playbook(body.playbook_name) or default_playbook(body.playbook_name)
    run_id = str(uuid4())
    stream = get_run_stream(run_id)
    stream.log(f"Dry run playbook {playbook.name}")
    gc = playbook.group_chat or {}
    policy = GroupChatPolicy(str(gc.get("policy") or GroupChatPolicy.SUPERVISOR_MODERATED.value))
    chat = GroupChat(
        participants=list(gc.get("participants") or list(playbook.roles.keys())),
        supervisor=str(gc.get("supervisor") or "coordinator"),
        policy=policy,
        workspace_id=playbook.workspace_id,
        run_id=run_id,
    )
    messages = await chat.dispatch(body.input, metadata={"dry_run": True})
    return {
        "run_id": run_id,
        "dry_run": True,
        "messages": [message.to_dict() for message in messages],
        "events": [event.to_dict() for event in stream.events()],
    }


@router.get("/runs/{run_id}/stream")
async def stream_run_events(run_id: str) -> StreamingResponse:
    stream = get_run_stream(run_id)

    async def generate():
        async for line in stream.iter_sse():
            yield line

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/runs/{run_id}/events")
async def run_events(run_id: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "stream_events": [event.to_dict() for event in get_run_stream(run_id).events()],
        "runtime_events": get_run_events(run_id),
    }


@router.post("/reset")
async def reset_runtime() -> dict[str, bool]:
    clear_messages()
    get_mcp_workbench().clear()
    return {"cleared": True}
