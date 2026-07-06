"""Optional cloud browser execution via Browser Use plugin."""

from __future__ import annotations

import os
from typing import Any


class CloudBrowserExecutor:
    """Delegates session creation to the bundled Browser Use provider when configured."""

    def __init__(self) -> None:
        self._enabled = os.environ.get("KEPRIX_BROWSER_CLOUD", "false").lower() == "true"

    @property
    def enabled(self) -> bool:
        return self._enabled

    def create_remote_session(self, task_name: str) -> dict[str, Any] | None:
        if not self._enabled:
            return None
        try:
            from plugins.browser.browser_use.provider import BrowserUseBrowserProvider

            provider = BrowserUseBrowserProvider()
            if not provider.is_available():
                return None
            session = provider.create_session(task_name)
            return {
                "provider": "browser-use",
                "session_id": session.get("session_id"),
                "connect_url": session.get("connect_url") or session.get("cdp_url"),
                "features": session.get("features") or {},
            }
        except Exception:
            return None

    def close_remote_session(self, session_id: str) -> bool:
        if not self._enabled:
            return False
        try:
            from plugins.browser.browser_use.provider import BrowserUseBrowserProvider

            provider = BrowserUseBrowserProvider()
            return bool(provider.close_session(session_id))
        except Exception:
            return False


_executor: CloudBrowserExecutor | None = None


def get_cloud_executor() -> CloudBrowserExecutor:
    global _executor
    if _executor is None:
        _executor = CloudBrowserExecutor()
    return _executor
