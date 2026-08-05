from typing import Any

from providers.base import InferenceProvider


class GroqProvider(InferenceProvider):
    def __init__(self, api_key: str):
        from groq import AsyncGroq

        self.client = AsyncGroq(api_key=api_key)

    async def complete(
        self,
        messages: list[dict[str, Any]],
        model: str = "llama-3.1-70b-versatile",
        **kwargs: Any,
    ) -> str:
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 4096),
        )
        return response.choices[0].message.content or ""
