"""Selenium Chrome driver."""

from __future__ import annotations

from typing import Any

from keprix.browser.drivers import BrowserDriverUnavailableError, PageSnapshot
from keprix.browser.element_map import BrowserElement


class SeleniumDriver:
    def __init__(self, *, headless: bool = True) -> None:
        self._headless = headless
        self._driver = None
        try:
            from selenium import webdriver  # noqa: F401
        except Exception as exc:
            raise BrowserDriverUnavailableError("Selenium is not installed") from exc

    def _ensure_driver(self) -> None:
        if self._driver is not None:
            return
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        options = Options()
        if self._headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        self._driver = webdriver.Chrome(options=options)

    def _collect_elements(self) -> list[dict[str, Any]]:
        assert self._driver is not None
        elements: list[dict[str, Any]] = []
        for index, handle in enumerate(
            self._driver.find_elements(
                "css selector",
                "a, button, input, textarea, select, [role='button']",
            )[:50]
        ):
            tag = handle.tag_name.lower()
            label = (
                handle.get_attribute("aria-label")
                or handle.get_attribute("name")
                or handle.get_attribute("placeholder")
                or (handle.text or "").strip()
                or tag
            )
            element_id = handle.get_attribute("id") or f"el-{index}"
            rect = handle.rect
            elements.append(
                BrowserElement(
                    element_id=element_id,
                    label=label[:120],
                    role=handle.get_attribute("role") or tag,
                    text=(handle.text or "")[:200],
                    x=int(rect.get("x", 0)),
                    y=int(rect.get("y", 0)),
                    width=int(rect.get("width", 0)),
                    height=int(rect.get("height", 0)),
                ).to_dict()
            )
        return elements

    def snapshot(self) -> PageSnapshot:
        self._ensure_driver()
        assert self._driver is not None
        return PageSnapshot(
            url=self._driver.current_url,
            title=self._driver.title,
            elements=self._collect_elements(),
            text=self._driver.find_element("tag name", "body").text,
        )

    def navigate(self, url: str) -> PageSnapshot:
        self._ensure_driver()
        assert self._driver is not None
        self._driver.get(url)
        return self.snapshot()

    def click(self, selector: str) -> PageSnapshot:
        self._ensure_driver()
        assert self._driver is not None
        try:
            self._driver.find_element("id", selector).click()
        except Exception:
            self._driver.find_element("xpath", f"//*[contains(text(), '{selector}')]").click()
        return self.snapshot()

    def fill(self, selector: str, value: str) -> PageSnapshot:
        self._ensure_driver()
        assert self._driver is not None
        try:
            self._driver.find_element("id", selector).send_keys(value)
        except Exception:
            self._driver.find_element("name", selector).send_keys(value)
        return self.snapshot()

    def screenshot(self) -> bytes:
        self._ensure_driver()
        assert self._driver is not None
        return self._driver.get_screenshot_as_png()
