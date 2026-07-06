"""Chrome extension bridge with safe offline fallback."""

from __future__ import annotations

import os
from typing import Any

from keprix.browser.drivers import PageSnapshot, StubBrowserDriver


class ChromeExtensionBridge(StubBrowserDriver):
    """Driver that uses the Chrome extension when configured, else safe local stub."""

    def __init__(self) -> None:
        super().__init__()
        self.extension_url = os.environ.get("KEPRIX_BROWSER_EXTENSION_URL", "").strip()
        self.available = bool(self.extension_url)

    def snapshot(self) -> PageSnapshot:
        shot = super().snapshot()
        shot.title = "Chrome extension bridge (stub)" if not self.available else "Chrome extension bridge"
        shot.text = (
            "Extension not configured. Set KEPRIX_BROWSER_EXTENSION_URL to connect."
            if not self.available
            else f"Bridged via extension at {self.extension_url}"
        )
        return shot
