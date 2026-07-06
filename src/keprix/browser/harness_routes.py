"""Browser harness, profile, skill, and benchmark HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.api.auth import require_api_auth
from keprix.browser.auth_context import load_auth_context
from keprix.browser.benchmark_runner import get_benchmark_runner
from keprix.browser.browser_profile import ProfileKind, get_profile_store
from keprix.browser.browser_skill import list_skills, run_skill
from keprix.browser.drivers import BrowserDriverUnavailableError
from keprix.browser.harness import get_harness_manager
from keprix.browser.browser_skill import register_playbook_nodes

harness_router = APIRouter(prefix="/api/browser", tags=["browser-harness"])


class HarnessSessionBody(BaseModel):
    workspace_id: str = "default"
    objective: str = Field(default="Agent browse task", min_length=1)
    url: str = "about:blank"
    profile_id: str | None = None


class ProfileBody(BaseModel):
    workspace_id: str = "default"
    name: str = Field(..., min_length=1)
    kind: ProfileKind = ProfileKind.PERSISTENT
    vault_credential_id: str | None = None


class SkillRunBody(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)
    approved: bool = False


class BenchmarkRunBody(BaseModel):
    benchmark_id: str
    workspace_id: str = "default"


@harness_router.get("/sessions")
async def list_browser_sessions(
    workspace_id: str = "default",
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    from keprix.browser.action_log import get_action_log
    from keprix.browser.session_store import get_session_store, session_mode

    store = get_session_store()
    log = get_action_log()
    sessions = []
    for record in store.list_recent(workspace_id):
        payload = record.to_dict()
        payload["mode"] = session_mode(record)
        payload["step_count"] = len(log.list_for_session(record.session_id))
        sessions.append(payload)
    return {"sessions": sessions}


@harness_router.get("/sessions/{session_id}/steps")
async def list_browser_session_steps(
    session_id: str,
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    from keprix.browser.action_log import get_action_log
    from keprix.browser.session_store import get_session_store, session_mode

    record = get_session_store().get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Browser session not found")
    steps = [row.to_dict() for row in get_action_log().list_for_session(session_id)]
    return {
        "session_id": session_id,
        "mode": session_mode(record),
        "steps": steps,
    }


@harness_router.post("/harness/session")
async def open_harness_session(
    body: HarnessSessionBody,
    user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    try:
        harness, record = get_harness_manager().open_session(
            workspace_id=body.workspace_id,
            objective=body.objective,
            url=body.url,
            profile_id=body.profile_id,
        )
    except BrowserDriverUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    auth = await load_auth_context(user_id=user, vault_credential_id=record.metadata.get("vault_credential_id"))
    snap = harness.capture()
    return {
        "session_id": harness.session_id,
        "trace_id": record.trace_id,
        "workspace_id": body.workspace_id,
        "profile_id": body.profile_id,
        "auth_context": auth,
        "snapshot": snap.to_dict(),
    }


@harness_router.get("/harness/{session_id}/snapshot")
async def harness_snapshot(session_id: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    harness = get_harness_manager().get(session_id)
    if harness is None:
        raise HTTPException(status_code=404, detail="Harness session not found")
    return harness.capture().to_dict()


@harness_router.get("/harness/sessions")
async def list_harness_sessions(
    workspace_id: str = "default",
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    return {"sessions": get_harness_manager().list_sessions(workspace_id)}


@harness_router.get("/profiles")
async def list_profiles(
    workspace_id: str = "default",
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    profiles = get_profile_store().list_profiles(workspace_id)
    return {"profiles": [profile.to_dict() for profile in profiles]}


@harness_router.post("/profiles")
async def create_profile(body: ProfileBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    profile = get_profile_store().create(
        workspace_id=body.workspace_id,
        name=body.name,
        kind=body.kind,
        vault_credential_id=body.vault_credential_id,
    )
    return profile.to_dict()


@harness_router.get("/skills")
async def get_skills(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"skills": list_skills()}


@harness_router.post("/skills/{skill_name}/run")
async def execute_skill(
    skill_name: str,
    session_id: str,
    body: SkillRunBody,
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    harness = get_harness_manager().get(session_id)
    if harness is None:
        raise HTTPException(status_code=404, detail="Harness session not found")
    try:
        params = dict(body.params)
        params["approved"] = body.approved
        return run_skill(skill_name, harness, params)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown browser skill") from exc


@harness_router.get("/benchmarks")
async def list_benchmarks(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"benchmarks": get_benchmark_runner().list_benchmarks()}


@harness_router.post("/benchmarks/run")
async def run_benchmark(body: BenchmarkRunBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    try:
        result = get_benchmark_runner().run(body.benchmark_id, workspace_id=body.workspace_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown benchmark") from exc
    return result.to_dict()


@harness_router.get("/benchmarks/{trace_id}")
async def get_benchmark_result(trace_id: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    result = get_benchmark_runner().get_result(trace_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Benchmark result not found")
    return result.to_dict()


@harness_router.get("/playbook/nodes")
async def playbook_browser_nodes(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    from keprix.playbook.runtime.graph import PlaybookGraph

    graph = PlaybookGraph("browser-skills")
    register_playbook_nodes(graph)
    nodes = [f"browser.{skill['name']}" for skill in list_skills()]
    return {"graph_id": graph.graph_id, "nodes": nodes}
