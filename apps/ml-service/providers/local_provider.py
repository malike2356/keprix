import hashlib
import math

from providers.base import EmbeddingProvider, STTProvider, TTSProvider, TranslationProvider


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """Local deterministic embeddings for tests and keyless development."""

    def __init__(self, dims: int = 1024):
        self._dims = dims

    async def embed(self, texts: list[str], model: str = "local-hash-1024") -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def dimensions(self, model: str = "local-hash-1024") -> int:
        return self._dims

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self._dims
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self._dims
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class TextBytesSTTProvider(STTProvider):
    async def transcribe(self, audio_bytes: bytes, language: str | None = None) -> str:
        return audio_bytes.decode("utf-8", errors="ignore").strip()


class SilentTTSProvider(TTSProvider):
    async def synthesize(self, text: str, voice_id: str) -> bytes:
        return f"audio placeholder: {text}".encode("utf-8")


class EchoTranslationProvider(TranslationProvider):
    async def translate(self, text: str, src_lang: str, tgt_lang: str) -> str:
        return text
