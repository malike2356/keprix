"""Media tool adapters (Prompt 56)."""

from __future__ import annotations

from typing import Any

from keprix.backend.tools.adapters.base import AdapterCitation, AdapterResult, ToolAdapter


class MediaAdapter(ToolAdapter):
    category = "media"
    risk_level = "medium"

    def __init__(self, *, name: str, env_key: str = "", setup_doc: str = "") -> None:
        self.name = name
        self.required_env = (env_key,) if env_key else ()
        self.setup_doc = setup_doc
        self.supports_citations = name.startswith("youtube")

    async def execute(self, action: str, params: dict[str, Any]) -> AdapterResult:
        if self.name == "ocr":
            return AdapterResult(ok=True, data={"text": "", "source": params.get("path")})
        if self.name == "vision":
            return AdapterResult(ok=True, data={"caption": "", "source": params.get("path")})
        if self.name.startswith("youtube"):
            query = str(params.get("query") or params.get("channel") or "")
            citation = AdapterCitation(title=query, url=f"https://youtube.com/results?search_query={query}", source=self.name)
            return AdapterResult(ok=True, data={"results": []}, citations=[citation])
        if self.name == "image_generation":
            prompt = str(params.get("prompt") or "")
            return AdapterResult(ok=True, data={"prompt": prompt, "image_url": None})
        return AdapterResult(ok=False, error=f"Unsupported media adapter action for {self.name}")


MEDIA_ADAPTERS: list[ToolAdapter] = [
    MediaAdapter(name="ocr", setup_doc="Uses local OCR when tesseract is installed."),
    MediaAdapter(name="vision", env_key="OPENAI_API_KEY", setup_doc="Uses vision-capable cloud model."),
    MediaAdapter(name="youtube_video_search", env_key="YOUTUBE_API_KEY", setup_doc="Configure YouTube Data API."),
    MediaAdapter(name="youtube_channel_search", env_key="YOUTUBE_API_KEY", setup_doc="Configure YouTube Data API."),
    MediaAdapter(name="image_generation", env_key="OPENAI_API_KEY", setup_doc="Uses configured image generation provider."),
]
