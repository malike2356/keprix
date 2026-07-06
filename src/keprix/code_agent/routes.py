"""Code agent HTTP routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.code_agent.code_agent import CodeAgent, CodeAgentConfig
from keprix.code_agent.modality_inputs import normalize_inputs
from keprix.code_agent.session_runner import CodingSessionRunner
from keprix.code_agent.session_store import get_coding_session_store
from keprix.code_agent.tool_collection import load_callable_tools, load_mcp_collection, merge_collections
from keprix.hub.agent_package import build_agent_package, install_agent_package, verify_agent_package
from keprix.hub.tool_package import build_tool_package, install_tool_package, verify_tool_package
from keprix.public_api.auth import require_developer_session

router = APIRouter(prefix="/api/code-agent", tags=["code-agent"])


class RunBody(BaseModel):
    task: str
    workspace_id: str = "default"
    provider: str = "docker"
    code: str | None = None
    text: str | None = None
    image_paths: list[str] = Field(default_factory=list)
    audio_transcript: str | None = None
    video_summary: str | None = None
    file_paths: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)


class McpMountBody(BaseModel):
    server_name: str
    tools: list[dict[str, Any]]


class HubInstallBody(BaseModel):
    package_dir: str
    kind: str = "agent"


class CreateSessionBody(BaseModel):
    objective: str
    workspace_id: str = "default"
    repo_path: str | None = None
    provider: str = "docker"
    control_center_session_id: str | None = None


class SessionTurnBody(BaseModel):
    user_input: str | None = None


@router.post("/run")
async def code_agent_run(body: RunBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    modalities = normalize_inputs(
        text=body.text or body.task,
        image_paths=body.image_paths,
        audio_transcript=body.audio_transcript,
        video_summary=body.video_summary,
        file_paths=body.file_paths,
        urls=body.urls,
    )
    agent = CodeAgent(CodeAgentConfig(workspace_id=body.workspace_id, provider=body.provider))
    try:
        result = agent.run_task(body.task, code=body.code, modalities=modalities)
    finally:
        agent.close()
    return {
        "ok": result.ok,
        "code": result.code,
        "result": result.result,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "errors": result.errors,
        "needs_approval": result.needs_approval,
        "provider": result.provider,
        "session_id": result.session_id,
    }


@router.post("/tools/mcp")
async def mount_mcp_tools(body: McpMountBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    collection = load_mcp_collection(body.server_name, body.tools, lambda name, args: {"tool": name, "args": args})
    return {"tools": collection.list_tools()}


@router.post("/sessions")
async def create_coding_session(body: CreateSessionBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    runner = CodingSessionRunner()
    record = runner.create_session(
        workspace_id=body.workspace_id,
        objective=body.objective,
        repo_path=body.repo_path,
        provider=body.provider,
        control_center_session_id=body.control_center_session_id,
    )
    return {"session": record.to_dict()}


@router.get("/sessions")
async def list_coding_sessions(status: str | None = None, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    rows = get_coding_session_store().list_sessions(status=status)
    return {"sessions": [row.to_dict() for row in rows]}


@router.get("/sessions/{session_id}")
async def get_coding_session(session_id: str, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    record = get_coding_session_store().get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": record.to_dict()}


@router.post("/sessions/{session_id}/turn")
async def run_coding_turn(
    session_id: str,
    body: SessionTurnBody,
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    runner = CodingSessionRunner()
    turn = runner.run_turn(session_id, user_input=body.user_input)
    return turn.to_dict()


@router.post("/sessions/{session_id}/pause")
async def pause_coding_session(session_id: str, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    record = CodingSessionRunner().pause(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": record.to_dict()}


@router.post("/sessions/{session_id}/resume")
async def resume_coding_session(session_id: str, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    record = CodingSessionRunner().resume(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": record.to_dict()}


@router.get("/sessions/{session_id}/trace")
async def coding_session_trace(session_id: str, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    events = CodingSessionRunner().read_trace(session_id)
    return {"events": events}


@router.post("/hub/install")
async def hub_install(body: HubInstallBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    package_dir = Path(body.package_dir)
    if not package_dir.is_dir():
        raise HTTPException(status_code=400, detail="package_dir does not exist")
    if body.kind == "tool":
        package = install_tool_package(package_dir, require_verified=True)
        verified = verify_tool_package(package)
    else:
        package = install_agent_package(package_dir, require_verified=True)
        verified = verify_agent_package(package)
    return {"ok": True, "name": package.name, "version": package.version, "verified": verified}
