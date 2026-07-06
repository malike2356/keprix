"""Headless Playwright browser driver."""

from __future__ import annotations

import re
from typing import Any

from keprix.browser.drivers import BrowserDriverUnavailableError, PageSnapshot
from keprix.browser.element_map import BrowserElement


class PlaywrightDriver:
    def __init__(self, *, headless: bool = True) -> None:
        self._headless = headless
        self._playwright = None
        self._browser = None
        self._page = None
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
        except Exception as exc:
            raise BrowserDriverUnavailableError("Playwright is not installed") from exc

    def _ensure_page(self) -> None:
        if self._page is not None:
            return
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self._headless)
        self._page = self._browser.new_page()

    def _collect_elements(self) -> list[dict[str, Any]]:
        assert self._page is not None
        elements: list[dict[str, Any]] = []
        handles = self._page.query_selector_all(
            "a, button, input, textarea, select, [role='button']"
        )
        for index, handle in enumerate(handles[:50]):
            tag = handle.evaluate("el => el.tagName").lower()
            label = (
                handle.get_attribute("aria-label")
                or handle.get_attribute("name")
                or handle.get_attribute("placeholder")
                or (handle.inner_text() or "").strip()
                or tag
            )
            element_id = handle.get_attribute("id") or f"el-{index}"
            box = handle.bounding_box() or {}
            elements.append(
                BrowserElement(
                    element_id=element_id,
                    label=label[:120],
                    role=handle.get_attribute("role") or tag,
                    text=(handle.inner_text() or "").strip()[:200],
                    x=int(box.get("x", 0)),
                    y=int(box.get("y", 0)),
                    width=int(box.get("width", 0)),
                    height=int(box.get("height", 0)),
                ).to_dict()
            )
        return elements

    def snapshot(self) -> PageSnapshot:
        self._ensure_page()
        assert self._page is not None
        text = self._page.inner_text("body")
        return PageSnapshot(
            url=self._page.url,
            title=self._page.title(),
            elements=self._collect_elements(),
            text=text,
        )

    def navigate(self, url: str) -> PageSnapshot:
        self._ensure_page()
        assert self._page is not None
        self._page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        return self.snapshot()

    def click(self, selector: str) -> PageSnapshot:
        self._ensure_page()
        assert self._page is not None
        locator = self._page.locator(f"#{selector}")
        if locator.count() == 0:
            locator = self._page.get_by_role("button", name=re.compile(selector, re.I))
        locator.first.click(timeout=10_000)
        return self.snapshot()

    def fill(self, selector: str, value: str) -> PageSnapshot:
        self._ensure_page()
        assert self._page is not None
        locator = self._page.locator(f"#{selector}")
        if locator.count() == 0:
            locator = self._page.locator(f"[name='{selector}']")
        locator.first.fill(value, timeout=10_000)
        return self.snapshot()

    def screenshot(self) -> bytes:
        self._ensure_page()
        assert self._page is not None
        return self._page.screenshot(type="png")

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
