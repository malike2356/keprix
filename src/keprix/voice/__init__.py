"""Voice wake word registry and detection (Prompt 46)."""

from keprix.voice.detector import WakeWordDetector
from keprix.voice.service import get_wake_registry
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
    "get_wake_registry",
]
