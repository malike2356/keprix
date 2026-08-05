"""Local Whisper STT adapter placeholder."""

from __future__ import annotations


class LocalWhisperSTT:
    name = "local_whisper"

    async def transcribe(self, audio: bytes) -> str:
        return audio.decode("utf-8", errors="ignore").strip()
