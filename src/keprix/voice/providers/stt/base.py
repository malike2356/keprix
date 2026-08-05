"""STT provider interface."""

from __future__ import annotations

from typing import Protocol


class STTProvider(Protocol):
    name: str

    async def transcribe(self, audio: bytes) -> str:
        ...
