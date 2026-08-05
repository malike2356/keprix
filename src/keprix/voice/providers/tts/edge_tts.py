"""Microsoft Edge TTS adapter placeholder."""

from __future__ import annotations


class EdgeTTS:
    name = "edge_tts"

    async def synthesize(self, text: str) -> bytes:
        return f"audio:{text}".encode("utf-8")
