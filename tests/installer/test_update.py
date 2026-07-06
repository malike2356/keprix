"""Update version comparison and release API."""

from __future__ import annotations

import json

import httpx
import pytest

from keprix.installer.update import (
    compare_versions,
    fetch_latest_release,
    is_update_available,
    save_rollback_state,
    load_rollback_state,
)


def test_compare_versions():
    assert compare_versions("0.1.0", "0.2.0") < 0
    assert compare_versions("1.0.0", "1.0.0") == 0
    assert compare_versions("2.0.0", "1.9.9") > 0


def test_is_update_available_with_mock_release():
    release = {"tag_name": "v0.2.0"}
    assert is_update_available("0.1.0", release) is True
    assert is_update_available("0.2.0", release) is False


def test_fetch_latest_release_mock():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"tag_name": "v0.2.0", "body": "changelog"})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        payload = fetch_latest_release(client=client)
    assert payload["tag_name"] == "v0.2.0"


def test_rollback_state_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_INSTALL_HOME", str(tmp_path))
    from keprix.installer import paths

    monkeypatch.setattr(paths, "get_install_root", lambda: tmp_path)
    save_rollback_state("0.1.0", {"keprix-backend": "keprix-backend:0.1.0"})
    loaded = load_rollback_state()
    assert loaded is not None
    assert loaded["previous_version"] == "0.1.0"
