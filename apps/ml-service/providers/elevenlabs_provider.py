from providers.base import TTSProvider

ELEVENLABS_DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"


class ElevenLabsProvider(TTSProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def synthesize(self, text: str, voice_id: str = ELEVENLABS_DEFAULT_VOICE) -> bytes:
        import httpx

        selected_voice = voice_id if voice_id and voice_id != "default" else ELEVENLABS_DEFAULT_VOICE
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{selected_voice}",
                headers={"xi-api-key": self.api_key, "Content-Type": "application/json"},
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                },
            )
            response.raise_for_status()
            return response.content
