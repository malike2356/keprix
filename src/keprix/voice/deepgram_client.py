"""Deepgram streaming STT facade used by the phone stream handler."""

from __future__ import annotations

from types import TracebackType
from keprix.compat import Self
class DeepgramStreamingSession:
    def __init__(self) -> None:
        self._chunks: list[bytes] = []

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None) -> None:
        return None

    async def send(self, pcm: bytes) -> None:
        self._chunks.append(pcm)

    async def finish(self) -> str:
        raw = b"".join(self._chunks)
        return raw.decode("utf-8", errors="ignore").strip()


class DeepgramStreamingClient:
    def session(self) -> DeepgramStreamingSession:
        return DeepgramStreamingSession()
