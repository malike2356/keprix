"""Provider-agnostic phone voice pipeline."""

from __future__ import annotations

from collections.abc import AsyncIterator

from keprix.channels.sensitive_scrub import scrub_secrets_for_speech
from keprix.voice.interruptions import InterruptionHandler
from keprix.voice.providers.llm.base import VoiceAgent
from keprix.voice.providers.stt.base import STTProvider
from keprix.voice.providers.tts.base import TTSProvider
from keprix.voice.session import VoiceSession
from keprix.voice.vad import VoiceActivityDetector


class VoicePipeline:
    def __init__(self, *, stt: STTProvider, agent: VoiceAgent, tts: TTSProvider, silence_prompt_chunks: int = 10) -> None:
        self.stt = stt
        self.agent = agent
        self.tts = tts
        self.vad = VoiceActivityDetector()
        self.interruption_handler = InterruptionHandler()
        self.silence_prompt_chunks = silence_prompt_chunks

    def _speech_safe(self, text: str, *, caller_text: str | None = None) -> str:
        extras = [caller_text] if caller_text else None
        return scrub_secrets_for_speech(text, extra_values=extras)

    async def run(self, audio_stream: AsyncIterator[bytes], session: VoiceSession) -> AsyncIterator[bytes]:
        caller_context = await self.agent.load_context(session.caller)
        silence_chunks = 0
        async for audio_chunk in audio_stream:
            if not self.vad.is_speech(audio_chunk):
                silence_chunks += 1
                if silence_chunks >= self.silence_prompt_chunks:
                    silence_chunks = 0
                    prompt = "Are you still there? I can keep helping when you're ready."
                    session.append("aiva", prompt, event="silence_prompt")
                    yield await self.tts.synthesize(self._speech_safe(prompt))
                continue
            silence_chunks = 0
            text = await self.stt.transcribe(audio_chunk)
            if not text or len(text.strip()) < 2:
                continue
            if self.agent.is_speaking:
                await self.interruption_handler.handle(session, text)
            session.append("caller", text)
            response = await self.agent.respond(text, session, caller_context)
            session.append("aiva", response.text, action=response.action)
            spoken = self._speech_safe(response.text, caller_text=text)
            audio = await self.tts.synthesize(spoken)
            yield audio
            await self.agent.save_to_memory(session, text, response)
