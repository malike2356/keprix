"""Base class and shared exceptions for all localization providers."""

from __future__ import annotations

from abc import ABC
from typing import Any


class LanguagePairUnsupported(Exception):
    def __init__(self, source: str, target: str, task: str, provider: str) -> None:
        super().__init__(
            f"{provider} does not support {task}: {source} -> {target}"
        )
        self.source = source
        self.target = target
        self.task = task
        self.provider = provider


class LocalizationProvider(ABC):
    name: str = ""
    capabilities: set[str] = set()

    def __init__(self, config: Any = None) -> None:
        self.config = config

    async def transcribe(
        self,
        audio_bytes: bytes,
        source_language: str | None = None,
        target_language: str = "en",
    ):
        raise NotImplementedError(f"{self.name} does not support transcription")

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        preserve_terms: list[str] | None = None,
    ):
        raise NotImplementedError(f"{self.name} does not support translation")

    async def synthesize_speech(
        self,
        text: str,
        language: str,
        voice_id: str | None = None,
    ):
        raise NotImplementedError(f"{self.name} does not support speech synthesis")

    async def health_check(self) -> dict:
        return {"status": "not_implemented", "provider": self.name}
