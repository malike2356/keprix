"""HTTP routes for Customer Concierge setup (Prompt 628)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from pydantic import AliasChoices, BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.customer_concierge.audience.context import (
    gate_tool_for_current_audience,
    get_audience_context,
)
from keprix.customer_concierge.audience.embed import new_embed_nonce, sign_widget_embed_config
from keprix.customer_concierge.audience.ingress import (
    check_message_rate,
    open_audience_session,
    resume_audience_session,
)
from keprix.customer_concierge.audience.retrieval_guard import forbidden_storage_access
from keprix.customer_concierge.audience.store import get_audience_store
from keprix.customer_concierge.capability_health import evaluate_capability_health
from keprix.customer_concierge.handoff import operator_takeover, release_to_ai, request_handoff
from keprix.customer_concierge.prompt_overlay import (
    build_concierge_persona_overlay,
    ensure_prompt_layer_registered,
    set_concierge_prompt_context,
)
from keprix.customer_concierge.published_knowledge import (
    get_knowledge_store,
    profile_policy,
)
from keprix.customer_concierge.readiness import evaluate_readiness
from keprix.customer_concierge.store import get_concierge_store
from keprix.customer_concierge.support_cases import (
    PRODUCT_SUPPORT_SCOPE,
    SCOPE as CUSTOMER_SUPPORT_SCOPE,
    get_support_case_store,
)
from keprix.customer_concierge.visitor_turn import run_visitor_turn
from keprix.customer_concierge.widget import public_widget_embed, public_widget_status

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


@router.get("/capability-health")
async def capability_health(
    persona_id: str = Query(default="default", alias="personaId"),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Honest provider/capability health (Prompt 629). Never fakes Zoom or delivery ready."""
    ws = _workspace(workspace_id, x_workspace_id, user)
    return evaluate_capability_health(
        workspace_id=ws,
        persona_id=persona_id,
        user_id=_uid(user),
    )


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


@router.get("/audience/identities")
async def list_audience_identities(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    rows = get_audience_store().list_identities(ws)
    return {"workspaceId": ws, "identities": [r.to_dict() for r in rows]}


@router.get("/audience/identities/{identity_id}/export")
async def export_audience_identity(
    identity_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    payload = get_audience_store().export_identity(ws, identity_id)
    if not payload:
        raise HTTPException(status_code=404, detail={"error_code": "identity_not_found"})
    return {"ok": True, **payload}


@router.delete("/audience/identities/{identity_id}")
async def erase_audience_identity(
    identity_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    result = get_audience_store().erase_identity(ws, identity_id)
    return {"ok": True, **result}


@router.post("/embed/sign")
async def sign_embed(
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    persona_id = str(body.get("personaId") or body.get("persona_id") or "default")
    import time

    nonce = new_embed_nonce()
    exp = int(time.time() * 1000) + int(body.get("ttlMs") or 15 * 60 * 1000)
    token = sign_widget_embed_config(
        {"personaId": persona_id, "workspaceId": ws, "nonce": nonce, "exp": exp}
    )
    return {"ok": True, "token": token, "nonce": nonce, "exp": exp}


@router.get("/knowledge")
async def list_knowledge(
    persona_id: str = Query(default="default", alias="personaId"),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    rows = get_knowledge_store().list_sources(ws, persona_id)
    profile = get_concierge_store().get(ws, persona_id)
    return {
        "workspaceId": ws,
        "personaId": persona_id,
        "sources": rows,
        "attachedSourceIds": list(profile.knowledge_source_ids) if profile else [],
        "scope": "tenant_customer_knowledge",
        "notProductSupportCorpus": True,
    }


@router.post("/knowledge")
async def upsert_knowledge(
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    persona_id = str(body.get("personaId") or body.get("persona_id") or "default")
    title = str(body.get("title") or "").strip()
    content = str(body.get("content") or "").strip()
    if not title or not content:
        raise HTTPException(status_code=400, detail={"error_code": "title_and_content_required"})
    row = get_knowledge_store().upsert_source(
        workspace_id=ws,
        persona_id=persona_id,
        title=title,
        content=content,
        source_type=str(body.get("type") or "faq"),
        language=str(body.get("language") or "en"),
        source_id=body.get("id"),
        created_by=_uid(user),
    )
    attach = bool(body.get("attachToProfile", True))
    if attach:
        store = get_concierge_store()
        profile = store.get(ws, persona_id)
        if profile:
            ids = list(profile.knowledge_source_ids)
            if row["id"] not in ids:
                ids.append(row["id"])
                store.upsert_step1(
                    workspace_id=ws,
                    persona_id=persona_id,
                    persona_name=profile.persona_name or "Concierge",
                    greeting_message=profile.greeting_message or "Hi",
                    business_name=profile.business_name or "",
                    business_description=profile.business_description or "",
                    escalation_email=profile.escalation_email or "",
                    knowledge_source_ids=ids,
                )
    return {"ok": True, "source": row}


@router.post("/knowledge/{source_id}/publish-state")
async def set_knowledge_publish_state(
    source_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    state = str(body.get("publishState") or body.get("publish_state") or "").strip()
    if state not in {"draft", "published", "archived"}:
        raise HTTPException(status_code=400, detail={"error_code": "invalid_publish_state"})
    row = get_knowledge_store().set_publish_state(
        workspace_id=ws,
        source_id=source_id,
        publish_state=state,  # type: ignore[arg-type]
        created_by=_uid(user),
    )
    if not row:
        raise HTTPException(status_code=404, detail={"error_code": "source_not_found"})
    return {"ok": True, "source": row}


@router.get("/knowledge/{source_id}/revisions")
async def knowledge_revisions(
    source_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    return {"sourceId": source_id, "revisions": get_knowledge_store().list_revisions(ws, source_id)}


@router.patch("/policy")
async def patch_policy(
    body: dict[str, Any] = Body(default_factory=dict),
    persona_id: str = Query(default="default", alias="personaId"),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    store = get_concierge_store()
    profile = store.get(ws, persona_id)
    if not profile:
        raise HTTPException(status_code=404, detail={"error_code": "profile_not_found"})
    channels = dict(profile.channel_config or {})
    policy = dict(channels.get("policy") or {})
    for key in (
        "languages",
        "confidenceThreshold",
        "sensitiveIntents",
        "slaFirstResponseMinutes",
        "slaResolutionMinutes",
        "contactCapture",
        "bookingEnabled",
    ):
        if key in body:
            policy[key] = body[key]
    channels["policy"] = policy
    updated = store.upsert_step2(
        workspace_id=ws,
        persona_id=persona_id,
        channels=channels,
        business_hours=profile.business_hours or {"timezone": "UTC", "windows": []},
        calendar_provider=profile.calendar_provider,
        conferencing_provider=profile.conferencing_provider,
        calendar_connected=profile.calendar_connected,
        conferencing_connected=profile.conferencing_connected,
        meeting_types=[
            m if isinstance(m, dict) else m.to_dict()
            for m in (profile.channel_config or {}).get("meetingTypes") or []
        ],
        ics_fallback_ok=profile.ics_fallback_ok,
    )
    return {"ok": True, "policy": profile_policy(updated), "profile": updated.to_dict()}


@router.get("/cases")
async def list_customer_cases(
    persona_id: str = Query(default="default", alias="personaId"),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    rows = get_support_case_store().list_cases(ws, persona_id=persona_id)
    return {
        "workspaceId": ws,
        "personaId": persona_id,
        "cases": rows,
        "scope": CUSTOMER_SUPPORT_SCOPE,
        "productSupportScope": PRODUCT_SUPPORT_SCOPE,
        "note": "These are tenant customer-support cases, not Keprix product-support tickets at /api/support",
    }


@router.get("/cases/{case_id}")
async def get_customer_case(
    case_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    case = get_support_case_store().get_case(ws, case_id)
    if not case:
        raise HTTPException(status_code=404, detail={"error_code": "case_not_found"})
    notes = get_support_case_store().list_internal_notes(ws, case_id=case_id)
    events = get_support_case_store().list_events(ws, case_id)
    return {"case": case, "internalNotes": notes, "events": events, "scope": CUSTOMER_SUPPORT_SCOPE}


@router.post("/cases/{case_id}/status")
async def set_case_status(
    case_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    status = str(body.get("status") or "")
    if status not in {"open", "pending_customer", "pending_operator", "resolved", "closed"}:
        raise HTTPException(status_code=400, detail={"error_code": "invalid_status"})
    case = get_support_case_store().transition(
        workspace_id=ws,
        case_id=case_id,
        status=status,  # type: ignore[arg-type]
        actor_type="operator",
        actor_id=_uid(user),
    )
    if not case:
        raise HTTPException(status_code=404, detail={"error_code": "case_not_found"})
    return {"ok": True, "case": case}


@router.post("/cases/{case_id}/notes")
async def add_case_note(
    case_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    case = get_support_case_store().get_case(ws, case_id)
    if not case:
        raise HTTPException(status_code=404, detail={"error_code": "case_not_found"})
    note_body = str(body.get("body") or "").strip()
    if not note_body:
        raise HTTPException(status_code=400, detail={"error_code": "body_required"})
    note = get_support_case_store().add_internal_note(
        workspace_id=ws,
        persona_id=str(case["personaId"]),
        body=note_body,
        author_user_id=_uid(user),
        case_id=case_id,
        audience_session_id=case.get("audienceSessionId"),
    )
    return {"ok": True, "note": note, "visibility": "owner_only"}


@router.post("/sessions/{session_id}/handoff")
async def operator_request_handoff(
    session_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    persona_id: str = Query(default="default", alias="personaId"),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    result = request_handoff(
        workspace_id=ws,
        persona_id=persona_id,
        audience_session_id=session_id,
        reason=str(body.get("reason") or "Operator requested handoff"),
        channel=str(body.get("channel") or "web"),
        conversation_summary=body.get("summary"),
    )
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result)
    return result


@router.post("/sessions/{session_id}/takeover")
async def session_takeover(
    session_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    result = operator_takeover(
        workspace_id=ws,
        audience_session_id=session_id,
        operator_user_id=_uid(user),
    )
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result)
    return result


@router.post("/sessions/{session_id}/release")
async def session_release(
    session_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    result = release_to_ai(
        workspace_id=ws,
        audience_session_id=session_id,
        operator_user_id=_uid(user),
    )
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result)
    return result


@router.get("/sessions/{session_id}/messages")
async def session_messages(
    session_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    messages = get_support_case_store().list_messages(ws, session_id)
    notes = get_support_case_store().list_internal_notes(ws)
    # Internal notes are included only on operator routes
    session_notes = [n for n in notes if n.get("audienceSessionId") == session_id]
    return {
        "sessionId": session_id,
        "messages": messages,
        "internalNotes": session_notes,
        "internalNotesVisibility": "owner_only",
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
    result = open_audience_session(
        workspace_id=workspace_id,
        persona_id=persona_id,
        channel=str(body.get("channel") or "web"),
        external_key=body.get("externalKey") or body.get("external_key"),
        origin=body.get("origin"),
        locale=body.get("locale"),
        display_name=body.get("displayName") or body.get("display_name"),
        email=body.get("email"),
        embed_token=body.get("embedToken") or body.get("embed_token"),
        embed_nonce=body.get("nonce"),
        consent_state=str(body.get("consentState") or "unknown"),
    )
    if not result.get("ok"):
        raise HTTPException(status_code=403, detail=result)
    ensure_prompt_layer_registered()
    set_concierge_prompt_context(workspace_id, persona_id)
    session = result["session"]
    return {
        "ok": True,
        "sessionId": session["id"],
        "widgetSessionToken": session.get("widgetSessionToken"),
        "greeting": result.get("greeting"),
        "personaName": result.get("personaName"),
        "businessName": result.get("businessName"),
        "principal": "audience_session",
        "actorType": "audience",
        "workspaceMember": False,
        "channel": session.get("channel"),
        "identityId": session.get("identityId"),
    }


@public_router.post("/{workspace_id}/{persona_id}/channel/session")
async def public_channel_session(
    workspace_id: str,
    persona_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Gateway channel (Telegram/WhatsApp/email/SMS/voice) audience session."""
    channel = str(body.get("channel") or "").strip().lower()
    if channel in {"", "web"}:
        raise HTTPException(status_code=400, detail={"error_code": "use_web_session_endpoint"})
    result = open_audience_session(
        workspace_id=workspace_id,
        persona_id=persona_id,
        channel=channel,
        external_key=str(body.get("externalKey") or body.get("external_key") or ""),
        display_name=body.get("displayName"),
        email=body.get("email"),
        locale=body.get("locale"),
        consent_state=str(body.get("consentState") or "unknown"),
    )
    if not result.get("ok"):
        raise HTTPException(status_code=403, detail=result)
    ensure_prompt_layer_registered()
    set_concierge_prompt_context(workspace_id, persona_id)
    session = result["session"]
    return {
        "ok": True,
        "sessionId": session["id"],
        "channel": channel,
        "principal": "audience_session",
        "workspaceMember": False,
        "greeting": result.get("greeting"),
        "identityId": session.get("identityId"),
    }


@public_router.post("/{workspace_id}/{persona_id}/session/{session_id}/message")
async def public_session_message(
    workspace_id: str,
    persona_id: str,
    session_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    resumed = resume_audience_session(
        workspace_id=workspace_id,
        persona_id=persona_id,
        session_id=session_id,
        widget_token=body.get("widgetSessionToken"),
    )
    if not resumed.get("ok"):
        # Preserve unpublished existing conversations via legacy widget rows when present
        legacy = get_concierge_store().get_session(session_id)
        if not legacy or legacy.workspace_id != workspace_id or not get_concierge_store().allow_widget_message(
            session_id
        ):
            raise HTTPException(status_code=403, detail=resumed)
    else:
        rate = check_message_rate(workspace_id, session_id)
        if not rate.get("allowed"):
            raise HTTPException(status_code=429, detail={"error_code": "rate_limited", **rate})

    # Optional tool attempt from client/agent loop: deny-by-default
    tool_name = str(body.get("tool") or body.get("toolName") or "").strip() or None
    if tool_name:
        if get_audience_context() is None:
            raise HTTPException(
                status_code=403,
                detail={"error_code": "audience_context_required", "tool": tool_name},
            )
        gate = gate_tool_for_current_audience(tool_name)
        if not gate.get("ok"):
            raise HTTPException(status_code=403, detail=gate)

    storage_target = str(body.get("storageTarget") or body.get("retrieve") or "")
    if storage_target and forbidden_storage_access(storage_target, require_audience=False):
        raise HTTPException(
            status_code=403,
            detail={"error_code": "private_storage_forbidden", "target": storage_target},
        )

    profile = get_concierge_store().get(workspace_id, persona_id)
    text = str(body.get("text") or "").strip()
    tool_args = body.get("toolArgs") or body.get("args") or {}
    if not isinstance(tool_args, dict):
        tool_args = {}
    turn = run_visitor_turn(
        workspace_id=workspace_id,
        persona_id=persona_id,
        session_id=session_id,
        text=text,
        tool_name=tool_name,
        tool_args=tool_args,
    )
    if not turn.get("ok"):
        raise HTTPException(status_code=403, detail=turn)
    # Never expose internal notes on public responses
    turn.pop("internalNotes", None)
    return {
        **turn,
        "sessionId": session_id,
        "published": bool(profile and profile.published),
        "workspaceMember": False,
        "principal": "audience_session",
        "internalNotesVisible": False,
    }
