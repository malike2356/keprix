"""Phone voice session management API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket
from pydantic import BaseModel

from keprix.api.auth import require_admin
from keprix.voice.cost_tracker import estimate_call_cost
from keprix.voice.provision import twilio_provisioning_plan
from keprix.voice.session import create_voice_session, get_voice_session, list_voice_sessions
from keprix.gateway.twilio_voice_webhook import TwilioVoiceWebhook
from keprix.gateway.voice_stream_handler import VoiceStreamHandler
from keprix.voice.call_finaliser import CallFinaliser
from keprix.voice.call_store import VoiceCallStore

router = APIRouter(prefix="/api/voice/phone", tags=["voice-phone"])
inbound_router = APIRouter(tags=["voice-inbound"])


class CreateSessionBody(BaseModel):
    caller: str
    called: str
    persona: str = "receptionist"
    business_id: str = "default"


class ProvisionBody(BaseModel):
    base_url: str
    country: str = "GB"


@router.get("/sessions")
async def sessions(status: str | None = None, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return {"sessions": [session.to_dict() for session in list_voice_sessions(status=status)]}


@router.post("/sessions")
async def create_session(body: CreateSessionBody, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return create_voice_session(caller=body.caller, called=body.called, persona=body.persona, business_id=body.business_id).to_dict()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    session = get_voice_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="voice session not found")
    return session.to_dict()


@router.post("/provision/twilio")
async def provision_twilio(body: ProvisionBody, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return twilio_provisioning_plan(body.base_url, body.country)


@router.get("/cost-estimate")
async def cost_estimate(seconds: int = 300, input_tokens: int = 850, output_tokens: int = 120, _admin: dict = Depends(require_admin)) -> dict[str, float]:
    return estimate_call_cost(seconds, input_tokens=input_tokens, output_tokens=output_tokens)


@inbound_router.post("/api/voice/inbound")
async def inbound_voice(request: Request):
    return await TwilioVoiceWebhook().handle_inbound(request)


@inbound_router.post("/api/voice/status")
async def inbound_voice_status(request: Request) -> dict[str, str | None]:
    form = await request.form()
    call_sid = str(form.get("CallSid") or "")
    status = str(form.get("CallStatus") or "")
    store = VoiceCallStore()
    record = await store.get(call_sid)
    if record and status in {"completed", "busy", "failed", "no-answer", "canceled"}:
        await CallFinaliser(store).finalise(record)
    return {"call_sid": call_sid, "status": status, "summary": record.summary if record else None}


@inbound_router.websocket("/api/voice/stream/{call_sid}")
async def inbound_voice_stream(websocket: WebSocket, call_sid: str) -> None:
    await VoiceStreamHandler(call_sid).run(websocket)
