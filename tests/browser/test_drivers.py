"""Driver factory tests."""

import pytest

from keprix.browser.chrome_extension_bridge import ChromeExtensionBridge
from keprix.browser.drivers import BrowserDriverUnavailableError, StubBrowserDriver, create_browser_driver


def test_create_browser_driver_uses_stub_when_allowed(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_BROWSER_ALLOW_STUB", "true")
    monkeypatch.setenv("KEPRIX_BROWSER_DRIVER", "playwright")

    class MissingPlaywright:
        def __init__(self, **_: object) -> None:
            raise BrowserDriverUnavailableError("missing")

    class MissingSelenium:
        def __init__(self, **_: object) -> None:
            raise BrowserDriverUnavailableError("missing")

    monkeypatch.setattr("keprix.browser.playwright_driver.PlaywrightDriver", MissingPlaywright)
    monkeypatch.setattr("keprix.browser.selenium_driver.SeleniumDriver", MissingSelenium)
    driver = create_browser_driver()
    assert isinstance(driver, StubBrowserDriver)


def test_create_browser_driver_raises_without_stub(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_BROWSER_ALLOW_STUB", "false")

    class MissingPlaywright:
        def __init__(self, **_: object) -> None:
            raise BrowserDriverUnavailableError("missing")

    class MissingSelenium:
        def __init__(self, **_: object) -> None:
            raise BrowserDriverUnavailableError("missing")

    monkeypatch.setattr("keprix.browser.playwright_driver.PlaywrightDriver", MissingPlaywright)
    monkeypatch.setattr("keprix.browser.selenium_driver.SeleniumDriver", MissingSelenium)
    with pytest.raises(BrowserDriverUnavailableError):
        create_browser_driver(allow_stub=False)


def test_extension_bridge_safe_stub(monkeypatch) -> None:
    monkeypatch.delenv("KEPRIX_BROWSER_EXTENSION_URL", raising=False)
    bridge = ChromeExtensionBridge()
    snapshot = bridge.snapshot()
    assert "Extension not configured" in snapshot.text
