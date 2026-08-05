from abc import ABC, abstractmethod
from typing import Any


class InferenceProvider(ABC):
    @abstractmethod
    async def complete(self, messages: list[dict[str, Any]], model: str, **kwargs: Any) -> str:
        raise NotImplementedError


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def dimensions(self, model: str) -> int:
        raise NotImplementedError


class STTProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, language: str | None) -> str:
        raise NotImplementedError


class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, voice_id: str) -> bytes:
        raise NotImplementedError


class TranslationProvider(ABC):
    @abstractmethod
    async def translate(self, text: str, src_lang: str, tgt_lang: str) -> str:
        raise NotImplementedError
