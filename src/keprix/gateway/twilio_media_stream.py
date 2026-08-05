"""Twilio Media Streams WebSocket bridge."""

from __future__ import annotations

import base64
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from keprix.voice.pipeline import VoicePipeline
from keprix.voice.providers.llm.keprix_agent import KeprixVoiceAgent
from keprix.voice.providers.stt.deepgram import DeepgramSTT
from keprix.voice.providers.tts.elevenlabs import ElevenLabsTTS
from keprix.voice.session import get_voice_session

router = APIRouter(tags=["twilio-media-stream"])


async def _single_chunk(data: bytes):
    yield data


@router.websocket("/api/gateway/twilio/stream/{session_id}")
async def twilio_media_stream(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    session = get_voice_session(session_id)
    if session is None:
        await websocket.close(code=4404)
        return
    pipeline = VoicePipeline(stt=DeepgramSTT(), agent=KeprixVoiceAgent(), tts=ElevenLabsTTS())
    try:
        while True:
            raw = await websocket.receive_text()
            event = json.loads(raw)
            if event.get("event") == "stop":
                session.finish()
                break
            payload = (event.get("media") or {}).get("payload")
            if not payload:
                continue
            audio = base64.b64decode(payload)
            async for response_audio in pipeline.run(_single_chunk(audio), session):
                await websocket.send_json({"event": "media", "media": {"payload": base64.b64encode(response_audio).decode("ascii")}})
    except WebSocketDisconnect:
        session.finish()
