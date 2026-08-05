from providers.base import EmbeddingProvider, STTProvider

OPENAI_DIMENSIONS = {
    "text-embedding-3-large": 3072,
    "text-embedding-3-small": 1536,
}


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=api_key)

    async def embed(self, texts: list[str], model: str = "text-embedding-3-large") -> list[list[float]]:
        response = await self.client.embeddings.create(input=texts, model=model)
        return [item.embedding for item in response.data]

    def dimensions(self, model: str = "text-embedding-3-large") -> int:
        return OPENAI_DIMENSIONS.get(model, 3072)


class OpenAISTTProvider(STTProvider):
    def __init__(self, api_key: str):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=api_key)

    async def transcribe(self, audio_bytes: bytes, language: str | None = None) -> str:
        response = await self.client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.mp3", audio_bytes),
            language=language,
        )
        return response.text
