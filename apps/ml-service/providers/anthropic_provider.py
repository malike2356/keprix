from typing import Any

from providers.base import InferenceProvider


class AnthropicProvider(InferenceProvider):
    def __init__(self, api_key: str):
        from anthropic import AsyncAnthropic

        self.client = AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        messages: list[dict[str, Any]],
        model: str = "claude-sonnet-4-6",
        **kwargs: Any,
    ) -> str:
        response = await self.client.messages.create(
            model=model,
            max_tokens=kwargs.get("max_tokens", 4096),
            messages=messages,
        )
        first = response.content[0]
        return getattr(first, "text", "")
