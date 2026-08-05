"""Per-call Twilio Media Stream handler."""

from __future__ import annotations

import base64
import json

from fastapi import WebSocket, WebSocketDisconnect

from keprix.gateway.voice_audio import build_twilio_media_message, mulaw_to_pcm, pcm_to_mulaw
from keprix.voice.call_finaliser import CallFinaliser
from keprix.voice.call_store import VoiceCallStore
from keprix.voice.deepgram_client import DeepgramStreamingClient
from keprix.voice.escalation import EscalationEngine
from keprix.voice.tts_client import TTSStreamingClient


class VoiceStreamHandler:
    def __init__(
        self,
        call_sid: str,
        *,
        call_store: VoiceCallStore | None = None,
        deepgram: DeepgramStreamingClient | None = None,
        tts: TTSStreamingClient | None = None,
        escalation: EscalationEngine | None = None,
    ) -> None:
        self.call_sid = call_sid
        self.call_store = call_store or VoiceCallStore()
        self.deepgram = deepgram or DeepgramStreamingClient()
        self.tts = tts or TTSStreamingClient()
        self.escalation = escalation or EscalationEngine()
        self.finaliser = CallFinaliser(self.call_store)
        self.state = "idle"

    async def run(self, websocket: WebSocket) -> None:
        await websocket.accept()
        record = await self.call_store.get(self.call_sid)
        if record is None:
            await websocket.close(code=4404)
            return
        stream_sid = ""
        try:
            async with self.deepgram.session() as dgram:
                async for raw in websocket.iter_text():
                    event = json.loads(raw)
                    stream_sid = event.get("streamSid") or stream_sid
                    if event.get("event") == "stop":
                        break
                    if event.get("event") != "media":
                        continue
                    audio = base64.b64decode((event.get("media") or {}).get("payload") or "")
                    await dgram.send(mulaw_to_pcm(audio))
                transcript = await dgram.finish()
            if transcript:
                record.add_turn("caller", transcript)
                if self.escalation.should_escalate(transcript, duration_seconds=record.duration_seconds or 0):
                    record.escalated = True
                    record.escalated_to = self.escalation.policy.transfer_to
                    response = self.escalation.handoff_message()
                else:
                    response = "Got it. Let me check that now, one moment."
                record.add_turn("aiva", response)
                async for pcm in self.tts.stream(response):
                    await websocket.send_text(build_twilio_media_message(pcm_to_mulaw(pcm), stream_sid=stream_sid))
        except WebSocketDisconnect:
            pass
        finally:
            await self.finaliser.finalise(record)
