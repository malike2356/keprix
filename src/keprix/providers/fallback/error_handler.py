"""Provider error classification for fallback decisions."""

from __future__ import annotations


class ProviderError(Exception):
    pass


class QuotaExhausted(ProviderError):
    pass


class AllProvidersExhausted(ProviderError):
    def __init__(self, message: str, *, tried: int, last_error: Exception | None = None, explanation: dict | None = None) -> None:
        super().__init__(message)
        self.tried = tried
        self.last_error = last_error
        self.explanation = explanation or {}


def classify_error(exc: Exception) -> str:
    text = str(exc).lower()
    if isinstance(exc, QuotaExhausted) or "quota" in text or "rate limit" in text or "429" in text:
        return "quota"
    if "timeout" in text or "temporar" in text or "503" in text or "502" in text:
        return "transient"
    return "provider_error"
