"""Screenshot storage for browser sessions."""

from __future__ import annotations

import secrets
from dataclasses import dataclass


@dataclass
class Screenshot:
    id: str
    data: bytes
    content_type: str = "image/png"


class ScreenshotStore:
    def __init__(self) -> None:
        self._items: dict[str, Screenshot] = {}

    def save(self, data: bytes, *, content_type: str = "image/png") -> Screenshot:
        shot = Screenshot(id=secrets.token_hex(8), data=data, content_type=content_type)
        self._items[shot.id] = shot
        return shot

    def get(self, screenshot_id: str) -> Screenshot | None:
        return self._items.get(screenshot_id)


screenshot_store = ScreenshotStore()
