"""Tests for upgrade/events.py."""

from __future__ import annotations

from keprix.upgrade.events import clear_listeners, emit_update_event, on_event


def test_emit_update_event_calls_listeners():
    clear_listeners()
    seen: list[dict] = []

    def handler(payload: dict) -> None:
        seen.append(payload)

    on_event("update_available", handler)
    emit_update_event("update_available", {"alert": {"id": "a1"}})
    assert seen == [{"alert": {"id": "a1"}}]
    clear_listeners()


def test_emit_update_event_ignores_listener_errors():
    clear_listeners()

    def bad_handler(_payload: dict) -> None:
        raise RuntimeError("boom")

    def good_handler(payload: dict) -> None:
        payload["ok"] = True

    on_event("update_available", bad_handler)
    on_event("update_available", good_handler)
    payload: dict = {}
    emit_update_event("update_available", payload)
    assert payload.get("ok") is True
    clear_listeners()


def test_clear_listeners_by_type():
    clear_listeners()
    seen: list[str] = []
    on_event("update_available", lambda _p: seen.append("update"))
    on_event("upgrade_email_requested", lambda _p: seen.append("email"))
    emit_update_event("update_available", {})
    emit_update_event("upgrade_email_requested", {})
    assert seen == ["update", "email"]
    clear_listeners("update_available")
    emit_update_event("update_available", {})
    emit_update_event("upgrade_email_requested", {})
    assert seen == ["update", "email", "email"]
    clear_listeners()
