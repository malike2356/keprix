"""HTTP routes for Customer Concierge setup (Prompt 628)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from pydantic import AliasChoices, BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.customer_concierge.prompt_overlay import (
    build_concierge_persona_overlay,
    ensure_prompt_layer_registered,
    set_concierge_prompt_context,
)
from keprix.customer_concierge.readiness import evaluate_readiness
from keprix.customer_concierge.store import get_concierge_store
from keprix.customer_concierge.widget import (
    gate_new_widget_session,
    public_widget_embed,
    public_widget_status,
)

router = APIRouter(prefix="/api/customer-concierge", tags=["customer-concierge"])
public_router = APIRouter(prefix="/api/customer-concierge/public", tags=["customer-concierge-public"])


def _uid(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "default")


def _workspace(
    workspace_id: str | None,
    x_workspace_id: str | None,
    user: dict[str, Any],
) -> str:
    return (workspace_id or x_workspace_id or _uid(user) or "default").strip() or "default"


class Step1Body(BaseModel):
    model_config = {"extra": "ignore"}

    persona_id: str = Field(default="default", validation_alias=AliasChoices("personaId", "persona_id"))
    persona_name: str = Field(validation_alias=AliasChoices("personaName", "persona_name"))
    greeting_message: str = Field(validation_alias=AliasChoices("greetingMessage", "greeting_message"))
    business_name: str = Field(validation_alias=AliasChoices("businessName", "business_name"))
    business_description: str = Field(
        validation_alias=AliasChoices("businessDescription", "business_description")
    )
    escalation_email: str = Field(validation_alias=AliasChoices("escalationEmail", "escalation_email"))
    knowledge_source_ids: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("knowledgeSourceIds", "knowledge_source_ids"),
    )


class Step2Body(BaseModel):
    model_config = {"extra": "ignore"}

    persona_id: str = Field(default="default", validation_alias=AliasChoices("personaId", "persona_id"))
    channels: dict[str, Any] = Field(default_factory=dict)
    business_hours: dict[str, Any] = Field(
        validation_alias=AliasChoices("businessHours", "business_hours")
    )
    calendar_provider: str | None = Field(
        default=None, validation_alias=AliasChoices("calendarProvider", "calendar_provider")
    )
    conferencing_provider: str | None = Field(
        default=None, validation_alias=AliasChoices("conferencingProvider", "conferencing_provider")
    )
    calendar_connected: bool = Field(
        default=False, validation_alias=AliasChoices("calendarConnected", "calendar_connected")
    )
    conferencing_connected: bool = Field(
        default=False,
        validation_alias=AliasChoices("conferencingConnected", "conferencing_connected"),
    )
    meeting_types: list[dict[str, Any]] = Field(
        default_factory=list, validation_alias=AliasChoices("meetingTypes", "meeting_types")
    )
    ics_fallback_ok: bool = Field(
        default=True, validation_alias=AliasChoices("icsFallbackOk", "ics_fallback_ok")
    )


@router.get("/profile")
async def get_profile(
    persona_id: str = Query(default="default", alias="personaId"),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    profile = get_concierge_store().get(ws, persona_id)
    return {"workspaceId": ws, "personaId": persona_id, "profile": profile.to_dict() if profile else None}


@router.post("/setup/step1")
async def setup_step1(
    body: Step1Body,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    if not all(
        [
            body.persona_name.strip(),
            body.greeting_message.strip(),
            body.business_name.strip(),
            body.business_description.strip(),
            body.escalation_email.strip(),
        ]
    ):
        raise HTTPException(status_code=400, detail="Required step1 fields missing")
    profile = get_concierge_store().upsert_step1(
        workspace_id=ws,
        persona_id=(body.persona_id or "default").strip() or "default",
        persona_name=body.persona_name.strip(),
        greeting_message=body.greeting_message.strip(),
        business_name=body.business_name.strip(),
        business_description=body.business_description.strip(),
        escalation_email=body.escalation_email.strip(),
        knowledge_source_ids=body.knowledge_source_ids,
    )
    return {"ok": True, "profile": profile.to_dict()}


@router.post("/setup/step2")
async def setup_step2(
    body: Step2Body,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    try:
        profile = get_concierge_store().upsert_step2(
            workspace_id=ws,
            persona_id=(body.persona_id or "default").strip() or "default",
            channels=body.channels,
            business_hours=body.business_hours,
            calendar_provider=body.calendar_provider,
            conferencing_provider=body.conferencing_provider,
            calendar_connected=body.calendar_connected,
            conferencing_connected=body.conferencing_connected,
            meeting_types=body.meeting_types,
            ics_fallback_ok=body.ics_fallback_ok,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "profile": profile.to_dict()}


@router.get("/readiness")
async def readiness(
    persona_id: str = Query(default="default", alias="personaId"),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    return evaluate_readiness(ws, persona_id)


@router.post("/publish")
async def publish(
    persona_id: str = Query(default="default", alias="personaId"),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    result = evaluate_readiness(ws, persona_id)
    if not result["ready"]:
        raise HTTPException(
            status_code=400,
            detail={"error": "Concierge is not ready to publish", "readiness": result},
        )
    profile = get_concierge_store().set_published(ws, persona_id, True)
    ensure_prompt_layer_registered()
    set_concierge_prompt_context(ws, persona_id)
    return {
        "ok": True,
        "profile": profile.to_dict(),
        "widget": public_widget_embed(ws, persona_id),
        "personaOverlay": build_concierge_persona_overlay(profile),
    }


@router.post("/unpublish")
async def unpublish(
    persona_id: str = Query(default="default", alias="personaId"),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    try:
        profile = get_concierge_store().set_published(ws, persona_id, False)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "profile": profile.to_dict()}


@router.get("/preview")
async def preview(
    persona_id: str = Query(default="default", alias="personaId"),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    profile = get_concierge_store().get(ws, persona_id)
    return {
        "workspaceId": ws,
        "personaId": persona_id,
        "visitorView": public_widget_status(profile),
        "personaOverlay": build_concierge_persona_overlay(profile) if profile else None,
    }


@public_router.get("/{workspace_id}/{persona_id}/status")
async def public_status(workspace_id: str, persona_id: str) -> dict[str, Any]:
    profile = get_concierge_store().get(workspace_id, persona_id)
    return public_widget_status(profile)


@public_router.post("/{workspace_id}/{persona_id}/session")
async def public_open_session(
    workspace_id: str,
    persona_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    store = get_concierge_store()
    profile = store.get(workspace_id, persona_id)
    gate = gate_new_widget_session(profile)
    if not gate["ok"]:
        raise HTTPException(status_code=403, detail=gate)
    assert profile is not None
    try:
        session = store.open_session(profile)
    except PermissionError:
        raise HTTPException(status_code=403, detail={"error_code": "concierge_unpublished"}) from None
    ensure_prompt_layer_registered()
    set_concierge_prompt_context(workspace_id, persona_id)
    return {
        "ok": True,
        "sessionId": session.id,
        "greeting": profile.greeting_message,
        "personaName": profile.persona_name,
        "businessName": profile.business_name,
        # Visitor is never a workspace member
        "principal": "audience_session",
        "workspaceMember": False,
    }


@public_router.post("/{workspace_id}/{persona_id}/session/{session_id}/message")
async def public_session_message(
    workspace_id: str,
    persona_id: str,
    session_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    store = get_concierge_store()
    session = store.get_session(session_id)
    if not session or session.workspace_id != workspace_id or session.persona_id != persona_id:
        raise HTTPException(status_code=404, detail={"error_code": "session_not_found"})
    if not store.allow_widget_message(session_id):
        raise HTTPException(status_code=403, detail={"error_code": "session_closed"})
    profile = store.get(workspace_id, persona_id)
    text = str(body.get("text") or "").strip()
    # Echo greeting-aware stub; full agent loop lands in later prompts
    reply = profile.greeting_message if not text else (
        f"Thanks for your message. A team member can help further via {profile.escalation_email}."
        if profile
        else "Thanks for your message."
    )
    return {
        "ok": True,
        "sessionId": session_id,
        "reply": reply,
        "published": bool(profile and profile.published),
        "workspaceMember": False,
    }
