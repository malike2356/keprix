"""OpenAI Whisper STT adapter placeholder."""

from __future__ import annotations


class OpenAIWhisperSTT:
    name = "openai_whisper"

    async def transcribe(self, audio: bytes) -> str:
        return audio.decode("utf-8", errors="ignore").strip()
