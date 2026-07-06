"""App Foundation SDK HTTP routes."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from keprix.public_api.auth import require_api_key, require_developer_session
from keprix.public_api.keys import ApiKeyContext
from keprix.sdk.delivery import deliver_plan
from keprix.sdk.domain_context import parse_message
from keprix.sdk.events import get_sdk_event_bus
from keprix.sdk.schemas import (
    ActionPlanModel,
    ConfirmRequest,
    DomainSchema,
    ExecuteRequest,
    RegisterAppRequest,
)
from keprix.sdk.store import get_sdk_store
from keprix.sdk.ts_eval_runner import run_eval_suite

router = APIRouter(prefix="/api/sdk", tags=["sdk"])

TYPESCRIPT_SDK_MANIFEST = {
    "package": "@keprix/sdk",
    "version": "0.1.0",
    "modules": [
        "agent",
        "workflow",
        "memory",
        "rag",
        "evals",
        "tools",
        "local-dev",
    ],
    "endpoints": {
        "agent_run": "/v1/chat/completions",
        "workflow_start": "/api/playbook-runs/start",
        "workflow_get": "/api/playbook-runs/{run_id}",
        "workflow_events": "/api/playbook-runs/{run_id}/events",
        "memory_list": "/api/memory/list",
        "memory_save": "/api/memory/save",
        "memory_search": "/api/memory/search",
        "rag_ingest": "/api/rag/ingest",
        "rag_search": "/api/rag/search",
        "documents_query": "/api/documents/query",
        "evals_run": "/api/sdk/typescript/evals/run",
        "typed_agents": "/api/typed-agents",
        "typed_agent_schemas": "/api/typed-agents/{name}/schemas",
        "typed_agent_run": "/api/typed-agents/{name}/run",
        "code_agent_sessions": "/api/code-agent/sessions",
        "conversations": "/api/conversations",
    },
    "examples": [
        "examples/basic-agent.ts",
        "examples/workflow.ts",
        "examples/rag-agent.ts",
    ],
}


@router.get("/typed-agents")
async def list_typed_agents_sdk(_session: str = Depends(require_developer_session)) -> dict:
    from keprix.typed_agents.registry import bootstrap_typed_agents, list_typed_agents

    bootstrap_typed_agents()
    return {"agents": list_typed_agents()}


@router.get("/typed-agents/{name}/schemas")
async def typed_agent_schemas_sdk(name: str, _session: str = Depends(require_developer_session)) -> dict:
    from keprix.typed_agents.registry import bootstrap_typed_agents, get_typed_agent
    from keprix.typed_agents.schemas import AgentRunContext

    bootstrap_typed_agents()
    agent = get_typed_agent(name)
    if agent is None:
        raise HTTPException(status_code=404, detail="Typed agent not found")
    return agent.export_schemas(AgentRunContext(workspace_id="default", user_id="sdk"))


@router.get("/typescript/manifest")
async def typescript_sdk_manifest(_session: str = Depends(require_developer_session)) -> dict:
    return TYPESCRIPT_SDK_MANIFEST


class EvalCaseModel(BaseModel):
    name: str = "unnamed"
    input: str = ""
    expect_contains: str | None = None
    expect_equals: str | None = None


class EvalSuiteRequest(BaseModel):
    suite_name: str = "typescript-sdk"
    cases: list[EvalCaseModel] = Field(default_factory=list)


@router.post("/typescript/evals/run")
async def run_typescript_evals(
    body: EvalSuiteRequest,
    _session: str = Depends(require_developer_session),
) -> dict:
    if not body.cases:
        raise HTTPException(status_code=400, detail="At least one eval case is required")
    return run_eval_suite(
        suite_name=body.suite_name,
        cases=[case.model_dump() for case in body.cases],
    )


@router.post("/apps/register")
async def register_app(
    body: RegisterAppRequest,
    ctx: ApiKeyContext = Depends(require_api_key),
) -> dict:
    store = get_sdk_store()
    row = store.register_app(body, api_token_id=ctx.key_id)
    return {"app_id": row["id"], "name": row["name"], "version": row["version"]}


@router.get("/apps")
async def list_apps(_session: str = Depends(require_developer_session)) -> dict:
    apps = get_sdk_store().list_apps()
    return {
        "apps": [
            {
                "id": app["id"],
                "name": app["name"],
                "version": app["version"],
                "webhook_url": app.get("webhook_url"),
                "last_seen_at": app.get("last_seen_at"),
                "entity_count": len(app.get("domain_schema", {}).get("entities", [])),
            }
            for app in apps
        ]
    }


@router.get("/apps/{app_id}")
async def get_app(app_id: str, _session: str = Depends(require_developer_session)) -> dict:
    app = get_sdk_store().get_app(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return app


@router.delete("/apps/{app_id}")
async def unregister_app(app_id: str, _session: str = Depends(require_developer_session)) -> dict:
    if not get_sdk_store().unregister_app(app_id):
        raise HTTPException(status_code=404, detail="App not found")
    return {"unregistered": True, "app_id": app_id}


@router.put("/apps/{app_id}/schema")
async def update_schema(
    app_id: str,
    domain: DomainSchema,
    _session: str = Depends(require_developer_session),
) -> dict:
    updated = get_sdk_store().update_schema(app_id, domain)
    if not updated:
        raise HTTPException(status_code=404, detail="App not found")
    return {"app_id": app_id, "domain": updated["domain_schema"]}


@router.post("/execute", response_model=ActionPlanModel)
async def execute_plan(
    body: ExecuteRequest,
    ctx: ApiKeyContext = Depends(require_api_key),
) -> ActionPlanModel:
    store = get_sdk_store()
    app = store.get_app(body.app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    store.touch_app(body.app_id)
    domain = DomainSchema.model_validate(app["domain_schema"])
    plan = parse_message(domain, body.message, session_id=body.session_id)
    status = "pending" if plan.requires_confirmation else "ready"
    saved = store.save_plan(body.app_id, plan, status=status)
    plan.plan_id = saved["id"]

    if not plan.requires_confirmation:
        webhook_url = app.get("webhook_url")
        if webhook_url:
            delivery = await deliver_plan(webhook_url, plan)
            store.update_plan(
                saved["id"],
                status="delivered" if delivery.get("status") == "delivered" else "failed",
                delivered_at=datetime.now(timezone.utc).isoformat(),
                delivery_response=delivery,
            )
        await get_sdk_event_bus().publish(body.app_id, plan.model_dump())
    else:
        await get_sdk_event_bus().publish(body.app_id, plan.model_dump())

    return plan


@router.post("/execute/confirm")
async def confirm_plan(
    body: ConfirmRequest,
    ctx: ApiKeyContext = Depends(require_api_key),
) -> dict:
    store = get_sdk_store()
    row = store.get_plan(body.plan_id)
    if not row:
        raise HTTPException(status_code=404, detail="Plan not found")
    if not body.confirmed:
        store.update_plan(body.plan_id, status="rejected")
        return {"plan_id": body.plan_id, "status": "rejected"}

    app = store.get_app(row["app_id"])
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    plan = ActionPlanModel.model_validate(row["plan"])
    plan.plan_id = row["id"]
    webhook_url = app.get("webhook_url")
    delivery = None
    if webhook_url:
        delivery = await deliver_plan(webhook_url, plan)
    store.update_plan(
        body.plan_id,
        status="delivered" if not webhook_url or delivery.get("status") == "delivered" else "failed",
        delivered_at=datetime.now(timezone.utc).isoformat(),
        delivery_response=delivery,
    )
    await get_sdk_event_bus().publish(row["app_id"], plan.model_dump())
    return {"plan_id": body.plan_id, "status": "delivered", "delivery": delivery}


@router.get("/apps/{app_id}/plans")
async def list_app_plans(app_id: str, _session: str = Depends(require_developer_session)) -> dict:
    store = get_sdk_store()
    if not store.get_app(app_id):
        raise HTTPException(status_code=404, detail="App not found")
    return {"plans": store.list_plans(app_id)}


@router.get("/execute/{plan_id}")
async def get_plan_status(plan_id: str, _ctx: ApiKeyContext = Depends(require_api_key)) -> dict:
    row = get_sdk_store().get_plan(plan_id)
    if not row:
        raise HTTPException(status_code=404, detail="Plan not found")
    return row


@router.get("/apps/{app_id}/stream")
async def stream_plans(app_id: str, request: Request, _ctx: ApiKeyContext = Depends(require_api_key)):
    store = get_sdk_store()
    if not store.get_app(app_id):
        raise HTTPException(status_code=404, detail="App not found")

    queue = get_sdk_event_bus().subscribe(app_id)

    async def event_generator():
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: plan\ndata: {json.dumps(payload)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            get_sdk_event_bus().unsubscribe(app_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
