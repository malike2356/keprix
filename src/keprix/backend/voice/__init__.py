"""Re-export voice wake modules under backend/voice (Prompt 46)."""

from keprix.voice.detector import WakeWordDetector
from keprix.voice.routes import router
from keprix.voice.wake import (
    WAKE_WORD_DEFAULTS,
    WAKE_WORD_MAX_COUNT,
    WAKE_WORD_MAX_LENGTH,
    WakeWordRegistry,
    WakeWordRoutingConfig,
)

__all__ = [
    "WAKE_WORD_DEFAULTS",
    "WAKE_WORD_MAX_COUNT",
    "WAKE_WORD_MAX_LENGTH",
    "WakeWordDetector",
    "WakeWordRegistry",
    "WakeWordRoutingConfig",
    "router",
]
