"""OpenAI TTS adapter placeholder."""

from __future__ import annotations


class OpenAITTS:
    name = "openai_tts"

    async def synthesize(self, text: str) -> bytes:
        return f"audio:{text}".encode("utf-8")
