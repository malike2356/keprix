"""Twilio Voice webhook handler."""

from __future__ import annotations

from html import escape

from fastapi import APIRouter, Request
from fastapi.responses import Response

from keprix.voice.personas.receptionist import receptionist_greeting
from keprix.voice.session import create_voice_session

router = APIRouter(tags=["twilio-voice"])


def twiml_response(*, say: str, stream_url: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"<Say>{escape(say)}</Say>"
        "<Connect>"
        f'<Stream url="{escape(stream_url)}" />'
        "</Connect>"
        "</Response>"
    )


@router.post("/api/gateway/twilio/voice")
async def handle_inbound_call(request: Request) -> Response:
    form = await request.form()
    caller = str(form.get("From") or "")
    called = str(form.get("To") or "")
    session = create_voice_session(caller=caller, called=called, persona="receptionist", business_id=called or "default")
    base = str(request.base_url).rstrip("/")
    ws_base = base.replace("https://", "wss://").replace("http://", "ws://")
    greeting = receptionist_greeting("the business")
    xml = twiml_response(say=greeting, stream_url=f"{ws_base}/api/gateway/twilio/stream/{session.session_id}")
    session.append("aiva", greeting, event="greeting")
    return Response(content=xml, media_type="application/xml")


@router.post("/api/gateway/twilio/status")
async def twilio_status(request: Request) -> dict[str, str]:
    form = await request.form()
    return {"call_sid": str(form.get("CallSid") or ""), "status": str(form.get("CallStatus") or "")}
