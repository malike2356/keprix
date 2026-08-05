"""Simple voice activity detection."""

from __future__ import annotations


class VoiceActivityDetector:
    def __init__(self, *, min_energy: int = 2) -> None:
        self.min_energy = min_energy

    def is_speech(self, audio: bytes) -> bool:
        if not audio:
            return False
        return any(abs(byte - 128) >= self.min_energy for byte in audio)
