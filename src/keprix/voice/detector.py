"""Local wake word detection helpers (runs on nodes, not the gateway)."""

from __future__ import annotations

from typing import Any


class WakeWordDetector:
    """Wraps substring or Whisper-backed wake phrase detection."""

    def __init__(self, triggers: list[str], backend: str = "substring") -> None:
        self.backend = backend
        self.triggers = [t.lower() for t in triggers]

    def update_triggers(self, triggers: list[str]) -> None:
        self.triggers = [t.lower() for t in triggers]

    def is_triggered(self, transcript: str) -> bool:
        text = transcript.lower().strip()
        return any(trigger in text for trigger in self.triggers)

    def matched_trigger(self, transcript: str) -> str | None:
        text = transcript.lower().strip()
        for trigger in self.triggers:
            if trigger in text:
                return trigger
        return None

    async def run_whisper_check(self, audio_bytes: bytes, *, language: str = "en") -> bool:
        if self.backend != "whisper":
            raise ValueError("run_whisper_check requires backend='whisper'")
        from keprix.backend.localization.transcription import transcribe_audio

        result = await transcribe_audio(audio_bytes, source_language=language)
        return self.is_triggered(result.transcript)

    def to_dict(self) -> dict[str, Any]:
        return {"backend": self.backend, "triggers": list(self.triggers)}
