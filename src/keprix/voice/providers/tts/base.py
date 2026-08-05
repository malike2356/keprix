"""TTS provider interface."""

from __future__ import annotations

from typing import Protocol


class TTSProvider(Protocol):
    name: str

    async def synthesize(self, text: str) -> bytes:
        ...
