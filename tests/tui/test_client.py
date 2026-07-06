"""TUI client tests."""

from __future__ import annotations

from keprix.tui.client import KeprixClient


def test_client_defaults() -> None:
    client = KeprixClient()
    assert client.base_url == "http://127.0.0.1:3333"
    assert "Content-Type" in client._headers()
