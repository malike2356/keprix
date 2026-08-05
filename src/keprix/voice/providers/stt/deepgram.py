"""Deepgram STT adapter placeholder."""

from __future__ import annotations


class DeepgramSTT:
    name = "deepgram"

    async def transcribe(self, audio: bytes) -> str:
        return audio.decode("utf-8", errors="ignore").strip()
