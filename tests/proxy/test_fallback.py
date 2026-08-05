"""Emergency fallback tests."""

from __future__ import annotations

import json

from keprix.proxy.fallback import disable_fallback, enable_fallback, fallback_secret, fallback_status
from keprix.proxy.paths import local_vault_path


def test_fallback_enable_secret_and_disable(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    local_vault_path().write_text(json.dumps({"secrets": {"openai-api-key": "sk-old"}}), encoding="utf-8")

    enabled = enable_fallback(hours=24)

    assert enabled["enabled"] is True
    assert fallback_status()["enabled"] is True
    assert fallback_secret("openai-api-key") == "sk-old"
    assert disable_fallback()["enabled"] is False
    assert fallback_secret("openai-api-key") is None


def test_fallback_expires(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    enable_fallback(hours=-1)

    assert fallback_status()["enabled"] is False
    assert fallback_status().get("expired") in {None, True}
