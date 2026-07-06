"""Browser drivers and factory."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class PageSnapshot:
    url: str = "about:blank"
    title: str = ""
    elements: list[dict[str, Any]] = field(default_factory=list)
    text: str = ""


class BrowserDriver(Protocol):
    def navigate(self, url: str) -> PageSnapshot: ...

    def click(self, selector: str) -> PageSnapshot: ...

    def fill(self, selector: str, value: str) -> PageSnapshot: ...

    def screenshot(self) -> bytes: ...

    def snapshot(self) -> PageSnapshot: ...


class BrowserDriverUnavailableError(RuntimeError):
    """Raised when no real browser driver is available."""


class StubBrowserDriver:
    """In-memory driver for unit tests and explicit stub mode."""

    def __init__(self) -> None:
        self._url = "about:blank"
        self._title = "Stub page"
        self._elements = [
            {"id": "search", "role": "textbox", "label": "Search"},
            {"id": "submit", "role": "button", "label": "Submit"},
        ]

    def navigate(self, url: str) -> PageSnapshot:
        self._url = url
        self._title = f"Stub: {url}"
        return self.snapshot()

    def click(self, selector: str) -> PageSnapshot:
        return self.snapshot()

    def fill(self, selector: str, value: str) -> PageSnapshot:
        return self.snapshot()

    def screenshot(self) -> bytes:
        return b"\x89PNG\r\n\x1a\nstub"

    def snapshot(self) -> PageSnapshot:
        return PageSnapshot(
            url=self._url,
            title=self._title,
            elements=list(self._elements),
            text=f"Stub browser at {self._url}",
        )


def create_browser_driver(*, allow_stub: bool | None = None) -> BrowserDriver:
    """Resolve Playwright, Selenium, extension bridge, or stub (tests only)."""
    if allow_stub is None:
        allow_stub = os.environ.get("KEPRIX_BROWSER_ALLOW_STUB", "true").lower() == "true"

    driver_pref = os.environ.get("KEPRIX_BROWSER_DRIVER", "playwright").lower()
    if driver_pref == "extension":
        from keprix.browser.chrome_extension_bridge import ChromeExtensionBridge

        return ChromeExtensionBridge()

    from keprix.browser.playwright_driver import PlaywrightDriver
    from keprix.browser.selenium_driver import SeleniumDriver

    factories = (
        [SeleniumDriver, PlaywrightDriver]
        if driver_pref == "selenium"
        else [PlaywrightDriver, SeleniumDriver]
    )
    for factory in factories:
        try:
            return factory()
        except BrowserDriverUnavailableError:
            continue

    if allow_stub:
        return StubBrowserDriver()
    raise BrowserDriverUnavailableError(
        "No browser driver available. Install Playwright "
        "(`pip install playwright && playwright install chromium`) "
        "or Selenium with Chrome WebDriver, or set KEPRIX_BROWSER_ALLOW_STUB=true for tests."
    )
