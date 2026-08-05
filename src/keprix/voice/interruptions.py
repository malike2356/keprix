"""Barge-in handling for phone voice sessions."""

from __future__ import annotations

from keprix.voice.session import VoiceSession


class InterruptionHandler:
    def __init__(self) -> None:
        self.count = 0

    async def handle(self, session: VoiceSession, text: str) -> dict[str, str]:
        self.count += 1
        session.status = "interrupted"
        session.append("caller", text, event="interrupt")
        return {"action": "stop_tts", "message": "Caller interrupted; stop current speech."}
