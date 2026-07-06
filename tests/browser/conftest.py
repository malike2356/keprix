"""Browser test fixtures."""

from __future__ import annotations

import pytest

from keprix.browser import action_engine as action_engine_module
from keprix.browser import action_log as action_log_module
from keprix.browser import benchmark_runner as benchmark_runner_module
from keprix.browser import harness as harness_module
from keprix.browser.browser_profile import BrowserProfileStore
from keprix.browser.drivers import StubBrowserDriver
from keprix.browser.session_store import HarnessSessionStore


@pytest.fixture(autouse=True)
def browser_test_isolation(request, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_BROWSER_ALLOW_STUB", "true")
    action_engine_module._engine = action_engine_module.ActionEngine()
    action_log_module._log = action_log_module.ActionLog(base_dir=tmp_path / "browser-log")
    harness_module._manager = harness_module.HarnessManager()
    benchmark_runner_module._runner = benchmark_runner_module.BrowserBenchmarkRunner()
    profile_root = tmp_path / "profiles"
    session_root = tmp_path / "sessions"
    import keprix.browser.browser_profile as profile_module
    import keprix.browser.session_store as session_module

    profile_module._store = BrowserProfileStore(base_dir=profile_root)
    session_module._store = HarnessSessionStore(base_dir=session_root)
    if request.module.__name__.endswith("test_drivers"):
        return
    monkeypatch.setattr(
        "keprix.browser.drivers.create_browser_driver",
        lambda **_: StubBrowserDriver(),
    )
