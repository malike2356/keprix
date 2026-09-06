"""Google Slides tool wrappers."""

from typing import Any

from .bridge import GoogleWorkspaceBridge


def gws_slides_create(
    title: str, slides: list[str] | None = None, confirm: bool = False
) -> dict[str, Any]:
    return GoogleWorkspaceBridge().slides_create(title, slides, confirm)
