from providers.base import EmbeddingProvider

VOYAGE_DIMENSIONS = {
    "voyage-3": 1024,
    "voyage-3-lite": 512,
    "voyage-code-3": 1024,
}


class VoyageProvider(EmbeddingProvider):
    def __init__(self, api_key: str):
        import voyageai

        self.client = voyageai.AsyncClient(api_key=api_key)

    async def embed(self, texts: list[str], model: str = "voyage-3") -> list[list[float]]:
        result = await self.client.embed(texts, model=model, input_type="document")
        return result.embeddings

    def dimensions(self, model: str = "voyage-3") -> int:
        return VOYAGE_DIMENSIONS.get(model, 1024)
