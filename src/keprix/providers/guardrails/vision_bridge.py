"""Vision bridge: route image-containing requests to vision-capable providers."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_VISION_PROVIDERS = frozenset({
    "openai", "anthropic", "gemini", "google", "xai",
    "openrouter", "mistral", "groq",
})


class VisionBridge:
    """Detect images in messages and ensure routing to a vision-capable provider."""

    def __init__(self, vision_providers: frozenset[str] | None = None) -> None:
        self._vision_providers = vision_providers or _VISION_PROVIDERS

    def has_images(self, messages: list[dict[str, Any]]) -> bool:
        """Return True if any message contains image content."""
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") in (
                        "image_url", "image", "image_base64"
                    ):
                        return True
            elif isinstance(content, str) and content.startswith("data:image"):
                return True
        return False

    def is_vision_capable(self, provider: str) -> bool:
        return provider in self._vision_providers

    def find_vision_provider(self, preferred: list[str]) -> str | None:
        """Return the first vision-capable provider from a preference list."""
        for p in preferred:
            if self.is_vision_capable(p):
                return p
        # Last resort: any known vision provider
        return next(iter(self._vision_providers), None)

    def strip_images(
        self, messages: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], int]:
        """Remove images from messages (fallback when no vision provider available).

        Returns (cleaned_messages, images_removed).
        """
        cleaned = []
        removed = 0
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, list):
                new_parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") in (
                        "image_url", "image", "image_base64"
                    ):
                        removed += 1
                        new_parts.append({
                            "type": "text",
                            "text": "[image removed: no vision-capable provider available]",
                        })
                    else:
                        new_parts.append(part)
                msg = dict(msg)
                msg["content"] = new_parts
            cleaned.append(msg)
        return cleaned, removed
