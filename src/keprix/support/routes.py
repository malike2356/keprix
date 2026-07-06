"""Support and customer success HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from keprix.api.auth import require_api_auth
from keprix.support.articles import list_templates
from keprix.support.diagnostics import build_diagnostics_bundle
from keprix.support.handoff import create_handoff
from keprix.support.knowledge import article_from_ticket, list_articles, search_articles
from keprix.support.lifecycle import assign_ticket, transition_ticket, triage_queue
from keprix.support.sla import sla_status
from keprix.support.incidents import (
    add_incident_update,
    create_incident,
    generate_public_incident_post,
)
from keprix.support.onboarding import checklist_progress, default_checklist, update_checklist_item
from keprix.support.schemas import (
    CreateIncidentBody,
    CreateTicketBody,
    HandoffBody,
    IncidentUpdateBody,
    UpdateChecklistBody,
)
from keprix.support.store import get_support_store
from keprix.support.tickets import attach_diagnostics, create_ticket, export_ticket

router = APIRouter(prefix="/api/support", tags=["support"])


@router.get("/community")
async def community_links(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    templates = list_templates()
    return {"links": templates["community_links"]}


@router.get("/articles/templates")
async def article_templates(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return list_templates()


@router.get("/setup-rescue")
async def setup_rescue(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"steps": list_templates()["setup_rescue"]}


@router.post("/diagnostics/bundle")
async def diagnostics_bundle(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return await build_diagnostics_bundle()


@router.get("/tickets")
async def list_tickets(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"tickets": get_support_store().list_tickets()}


@router.post("/tickets")
async def new_ticket(body: CreateTicketBody, user: str = Depends(require_api_auth)) -> dict[str, Any]:
    ticket = create_ticket(
        category=body.category,
        subject=body.subject.strip(),
        description=body.description.strip(),
        user_id=user,
        attach_diagnostics=body.attach_diagnostics,
    )
    if body.attach_diagnostics:
        ticket = await attach_diagnostics(ticket["id"]) or ticket
    return {"ticket": ticket}


@router.get("/tickets/triage")
async def support_triage_queue(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"tickets": triage_queue()}


@router.get("/tickets/{ticket_id}/export")
async def export_support_ticket(ticket_id: str, _user: str = Depends(require_api_auth)) -> Response:
    payload = export_ticket(ticket_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="keprix-ticket-{ticket_id}.json"'},
    )


@router.get("/incidents")
async def list_incidents(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"incidents": get_support_store().list_incidents()}


@router.post("/incidents")
async def new_incident(body: CreateIncidentBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    incident = create_incident(title=body.title.strip(), severity=body.severity, summary=body.summary.strip())
    return {"incident": incident}


@router.post("/incidents/{incident_id}/updates")
async def incident_update(
    incident_id: str,
    body: IncidentUpdateBody,
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    incident = add_incident_update(incident_id, message=body.message.strip(), status=body.status)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"incident": incident}


@router.post("/incidents/{incident_id}/public-post")
async def incident_public_post(incident_id: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    store = get_support_store()
    incident = store.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    post = generate_public_incident_post(incident)
    incident["public_post"] = post
    store.update_incident(incident_id, incident)
    return {"public_post": post}


@router.get("/onboarding/checklist")
async def onboarding_checklist(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    items = default_checklist()
    return {"items": items, "progress": checklist_progress(items)}


@router.patch("/onboarding/checklist")
async def patch_checklist(body: UpdateChecklistBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    items = update_checklist_item(body.item_id, completed=body.completed)
    return {"items": items, "progress": checklist_progress(items)}


@router.post("/handoff")
async def handoff_request(body: HandoffBody, user: str = Depends(require_api_auth)) -> dict[str, Any]:
    record = await create_handoff(
        category=body.category,
        summary=body.summary.strip(),
        privacy=body.privacy,
        contact_email=body.contact_email,
        user_id=user,
    )
    return {"handoff": record}


class TicketTransitionBody(BaseModel):
    status: str
    comment: str | None = None


class TicketAssignBody(BaseModel):
    assignee: str


@router.post("/tickets/{ticket_id}/transition")
async def ticket_transition(
    ticket_id: str,
    body: TicketTransitionBody,
    user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    try:
        ticket = transition_ticket(ticket_id, status=body.status, actor=user, comment=body.comment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"ticket": ticket}


@router.post("/tickets/{ticket_id}/assign")
async def ticket_assign(ticket_id: str, body: TicketAssignBody, user: str = Depends(require_api_auth)) -> dict[str, Any]:
    ticket = assign_ticket(ticket_id, assignee=body.assignee.strip(), actor=user)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"ticket": ticket}


@router.get("/tickets/{ticket_id}/sla")
async def ticket_sla(ticket_id: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    ticket = get_support_store().get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"sla": sla_status(ticket)}


@router.get("/knowledge")
async def knowledge_articles(q: str | None = None, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    articles = search_articles(q or "") if q else list_articles()
    return {"articles": articles}


@router.post("/tickets/{ticket_id}/knowledge")
async def ticket_to_knowledge(ticket_id: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    article = article_from_ticket(ticket_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"article": article}
