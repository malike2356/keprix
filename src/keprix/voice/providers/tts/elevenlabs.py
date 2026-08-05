"""ElevenLabs TTS adapter placeholder."""

from __future__ import annotations


class ElevenLabsTTS:
    name = "elevenlabs"

    async def synthesize(self, text: str) -> bytes:
        return f"audio:{text}".encode("utf-8")
