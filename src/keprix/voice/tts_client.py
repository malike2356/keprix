"""Streaming TTS facade for phone voice output."""

from __future__ import annotations

from collections.abc import AsyncIterator


class TTSStreamingClient:
    def __init__(self) -> None:
        self.interrupted = False

    async def stream(self, text: str, voice_id: str = "default") -> AsyncIterator[bytes]:
        self.interrupted = False
        for part in text.split(". "):
            if self.interrupted:
                break
            yield f"audio:{voice_id}:{part}".encode("utf-8")

    def interrupt(self) -> None:
        self.interrupted = True
