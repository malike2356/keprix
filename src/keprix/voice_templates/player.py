"""Assemble voice responses from templates, TTS, or text-only fallbacks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from keprix.voice_templates.audio_utils import concatenate_audio
from keprix.voice_templates.library import VoiceTemplateLibrary, get_template_library
from keprix.voice_templates.store import get_voice_template_store
from keprix.voice_templates.tts_bridge import supports_tts, synthesize_to_wav

AssemblyMethod = Literal["template", "template_tts_hybrid", "tts", "text_only"]


@dataclass
class VoiceResponseAssembly:
    audio_url: str | None
    transcript: str
    method: AssemblyMethod
    template_id: str | None = None


class VoicePlayer:
    def __init__(self, library: VoiceTemplateLibrary | None = None) -> None:
        self._library = library or get_template_library()
        self._store = get_voice_template_store()

    async def assemble_response(
        self,
        category_id: str,
        language_code: str,
        dynamic_text: str | None,
        full_text_fallback: str,
        workspace_id: str,
    ) -> VoiceResponseAssembly:
        template = await self._library.get_template(category_id, language_code, workspace_id)
        is_dynamic = self._library.is_dynamic_category(category_id)

        if template and not is_dynamic:
            await self._library.increment_play_count(template.id)
            return VoiceResponseAssembly(
                audio_url=f"/api/voice-templates/{template.id}/audio",
                transcript=template.transcript,
                method="template",
                template_id=template.id,
            )

        if template and is_dynamic and dynamic_text:
            template_audio = self._store.get_audio_bytes(
                template.audio_file_id, template.workspace_id
            )
            if template_audio:
                dynamic_audio = synthesize_to_wav(dynamic_text, language_code)
                if dynamic_audio:
                    combined = concatenate_audio(template_audio, dynamic_audio)
                    token = self._store.save_temp_audio(combined, language_code)
                    await self._library.increment_play_count(template.id)
                    return VoiceResponseAssembly(
                        audio_url=f"/api/voice-templates/temp/{token}/audio",
                        transcript=f"{template.transcript} {dynamic_text}".strip(),
                        method="template_tts_hybrid",
                        template_id=template.id,
                    )

        if supports_tts(language_code):
            audio = synthesize_to_wav(full_text_fallback, language_code)
            if audio:
                token = self._store.save_temp_audio(audio, language_code)
                return VoiceResponseAssembly(
                    audio_url=f"/api/voice-templates/temp/{token}/audio",
                    transcript=full_text_fallback,
                    method="tts",
                    template_id=None,
                )

        return VoiceResponseAssembly(
            audio_url=None,
            transcript=full_text_fallback,
            method="text_only",
            template_id=None,
        )


_player: VoicePlayer | None = None


def get_voice_player() -> VoicePlayer:
    global _player
    if _player is None:
        _player = VoicePlayer()
    return _player


def reset_voice_player() -> None:
    global _player
    _player = None
