"""Pre-recorded voice template library with TTS hybrid assembly (Prompt 49)."""

from keprix.voice_templates.library import (
    get_template_library,
    register_domain_category,
    reset_template_library,
)
from keprix.voice_templates.player import VoicePlayer, get_voice_player

__all__ = [
    "VoicePlayer",
    "get_template_library",
    "get_voice_player",
    "register_domain_category",
    "reset_template_library",
]
