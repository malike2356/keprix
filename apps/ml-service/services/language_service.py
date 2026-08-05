from __future__ import annotations

import base64
from typing import Any

from providers.base import STTProvider, TTSProvider, TranslationProvider
from utils.caching import get_cached, set_cached
from utils.errors import UnsupportedLanguageError

SUPPORTED_AUDIO_TYPES = {"audio/ogg", "audio/mp3", "audio/wav", "audio/mpeg", "audio/webm"}
TWI_HINTS = {"mepa", "kyew", "wo", "akwaaba", "medaase"}


class LanguageService:
    def __init__(self, stt: STTProvider, tts: TTSProvider, translator: TranslationProvider):
        self.stt = stt
        self.tts = tts
        self.translator = translator

    def detect_language(self, text: str) -> dict[str, Any]:
        normalized = text.strip().lower()
        if any(token in normalized.split() for token in TWI_HINTS):
            return {"language": "tw", "confidence": 0.85, "script": "Latn"}
        if len(normalized) < 10:
            return {"language": "en", "confidence": 0.5, "script": "Latn"}
        try:
            from langdetect import LangDetectException, detect_langs

            langs = detect_langs(text)
            top = langs[0]
            return {"language": top.lang, "confidence": round(top.prob, 3), "script": "Latn"}
        except Exception:
            return {"language": "en", "confidence": 0.0, "script": "Latn"}

    async def translate(self, text: str, src_lang: str, tgt_lang: str) -> dict[str, str]:
        if src_lang == "auto":
            src_lang = str(self.detect_language(text)["language"])
        if src_lang == tgt_lang:
            return {"translated_text": text, "src_lang": src_lang}

        cache_payload = {"text": text, "src": src_lang, "tgt": tgt_lang}
        cached = await get_cached("translate", cache_payload)
        if cached is not None:
            return cached

        translated = await self.translator.translate(text, src_lang, tgt_lang)
        result = {"translated_text": translated, "src_lang": src_lang}
        await set_cached("translate", cache_payload, result, ttl=3600)
        return result

    async def transcribe(self, audio_b64: str, mime_type: str, language: str | None = None) -> dict[str, str | None]:
        if mime_type not in SUPPORTED_AUDIO_TYPES:
            raise UnsupportedLanguageError(f"Unsupported mime type: {mime_type}")
        audio_bytes = base64.b64decode(audio_b64)
        lang_hint = None if language in {None, "auto"} else language
        transcript = (await self.stt.transcribe(audio_bytes, lang_hint)).strip()
        detected_language = None
        if language == "auto" and transcript:
            detected_language = str(self.detect_language(transcript).get("language"))
        return {"text": transcript, "detected_language": detected_language}

    async def synthesize(self, text: str, voice_id: str = "") -> dict[str, str]:
        audio_bytes = await self.tts.synthesize(text, voice_id or "default")
        return {"audio_b64": base64.b64encode(audio_bytes).decode("utf-8"), "mime_type": "audio/mpeg"}
