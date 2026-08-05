from providers.base import STTProvider


class WhisperLocalProvider(STTProvider):
    def __init__(self, model_path: str = "medium"):
        self._model_path = model_path
        self._model = None

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self._model_path, device="cpu", compute_type="int8")
        return self._model

    async def transcribe(self, audio_bytes: bytes, language: str | None = None) -> str:
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._transcribe_sync, audio_bytes, language)

    def _transcribe_sync(self, audio_bytes: bytes, language: str | None) -> str:
        import io

        model = self._get_model()
        segments, _info = model.transcribe(
            io.BytesIO(audio_bytes),
            language=language if language and language != "auto" else None,
            beam_size=5,
        )
        return " ".join(segment.text for segment in segments).strip()
