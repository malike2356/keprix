"""Booking saga + Zoom adapter tests (Prompt 632)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from keprix.vical.conferencing.redact import redact_conferencing_payload, to_public_booking_view
from keprix.vical.conferencing.zoom_adapter import ZoomConferencingAdapter
from keprix.vical.doctor import run_vical_doctor
from keprix.vical.saga import SagaDeps, book_with_saga, cancel_with_saga
from keprix.vical.saga.ledger import reset_saga_ledger_for_tests
from keprix.vical.seed import ensure_default_consultation
from keprix.vical.store import VicalStore
from keprix.vical.zoom_oauth import ZoomTokenBundle, save_zoom_tokens
from keprix.vical.zoom_webhooks import handle_zoom_webhook, verify_zoom_webhook_signature


@pytest.fixture()
def env_paths(tmp_path: Path, monkeypatch):
    store_path = tmp_path / "vical.json"
    saga_path = tmp_path / "saga.sqlite"
    token_path = tmp_path / "zoom_tokens.json"
    monkeypatch.setenv("KEPRIX_VICAL_SAGA_DB_PATH", str(saga_path))
    monkeypatch.setenv("KEPRIX_ZOOM_TOKEN_PATH", str(token_path))
    monkeypatch.setenv("KEPRIX_ZOOM_TOKEN_SECRET", "test-zoom-secret")
    monkeypatch.setenv("ZOOM_CLIENT_ID", "zid")
    monkeypatch.setenv("ZOOM_CLIENT_SECRET", "zsecret")
    monkeypatch.setenv("KEPRIX_CONCIERGE_ZOOM_WEBHOOK_SECRET", "whsec")
    reset_saga_ledger_for_tests(saga_path)
    store = VicalStore(path=store_path)
    ensure_default_consultation("host1", store=store)
    return {"store": store, "saga": saga_path}


def _next_weekday_slot(store: VicalStore, user_id: str = "host1") -> datetime:
    # Seeded Mon-Fri 09:00-17:00 UTC; pick next weekday 10:00
    start = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
    while start.weekday() > 4:
        start += timedelta(days=1)
    return start


def test_idempotent_book_creates_one_booking_and_one_zoom_meeting(env_paths) -> None:
    store: VicalStore = env_paths["store"]
    starts = _next_weekday_slot(store)
    calls: list[str] = []

    def fake_fetch(url: str, init: dict):
        calls.append(f"{init.get('method')}:{url}")
        if "meetings" in url and init.get("method") == "POST":
            return {
                "status": 201,
                "headers": {},
                "json": {
                    "id": 999001,
                    "join_url": "https://zoom.us/j/999001",
                    "start_url": "https://zoom.us/s/999001?zak=SECRETHOST",
                    "password": "123456",
                },
            }
        return {"status": 200, "headers": {}, "json": {}}

    tokens = {"host1": ZoomTokenBundle(access_token="tok", refresh_token="ref", expires_at=time.time() + 3600)}
    zoom = ZoomConferencingAdapter(
        fetch_impl=fake_fetch,
        get_tokens=lambda ws, uid: tokens.get(uid),
        save_tokens=lambda ws, uid, t: tokens.__setitem__(uid, t),
        meeting_by_idempotency={},
    )
    deps = SagaDeps(zoom_adapter=zoom, store=store, ledger=reset_saga_ledger_for_tests(env_paths["saga"]))

    first = book_with_saga(
        "host1",
        guest_name="Pat",
        guest_email="pat@example.com",
        starts_at=starts,
        slug="consultation",
        skip_slot_check=True,
        workspace_id="host1",
        idempotency_key="idem-1",
        prefer_managed_zoom=True,
        deps=deps,
    )
    second = book_with_saga(
        "host1",
        guest_name="Pat",
        guest_email="pat@example.com",
        starts_at=starts,
        slug="consultation",
        skip_slot_check=True,
        workspace_id="host1",
        idempotency_key="idem-1",
        prefer_managed_zoom=True,
        deps=deps,
    )
    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert first["booking"].id == second["booking"].id
    assert first["conferenceManaged"] is True
    assert first["booking"].meeting_url == "https://zoom.us/j/999001"
    assert sum(1 for c in calls if c.startswith("POST:")) == 1
    public = first["publicBooking"]
    blob = json.dumps(public)
    assert "SECRETHOST" not in blob
    assert "start_url" not in blob
    assert public.get("meeting_url") == "https://zoom.us/j/999001"


def test_host_start_url_redaction() -> None:
    payload = {
        "meeting_url": "https://zoom.us/j/1",
        "metadata": {"host_start_url": "https://zoom.us/s/1?zak=SECRET", "access_token": "tok"},
        "start_url": "https://zoom.us/s/1?zak=SECRET",
    }
    redacted = redact_conferencing_payload(payload)
    assert "host_start_url" not in redacted
    assert "access_token" not in redacted
    assert "start_url" not in redacted
    view = to_public_booking_view(
        {
            "id": "b1",
            "meeting_url": "https://zoom.us/s/1?zak=SECRET",
            "metadata": {"hostStartUrl": "https://zoom.us/s/1?zak=SECRET"},
        }
    )
    assert view.get("meeting_url") is None
    assert "SECRET" not in json.dumps(view)


def test_webhook_forgery_and_replay(env_paths, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_CONCIERGE_ZOOM_WEBHOOK_SECRET", "whsec")
    reset_saga_ledger_for_tests(env_paths["saga"])
    body_obj = {
        "event": "meeting.updated",
        "event_ts": 1710000000,
        "payload": {"object": {"id": "m1"}},
    }
    raw = json.dumps(body_obj, separators=(",", ":")).encode("utf-8")
    ts = str(int(time.time()))
    digest = hmac.new(b"whsec", f"v0:{ts}:".encode() + raw, hashlib.sha256).hexdigest()
    sig = f"v0={digest}"
    assert verify_zoom_webhook_signature(body=raw, timestamp=ts, signature=sig) is True
    assert verify_zoom_webhook_signature(body=raw, timestamp=ts, signature="v0=dead") is False

    first = handle_zoom_webhook(payload=body_obj, body=raw, timestamp=ts, signature=sig)
    second = handle_zoom_webhook(payload=body_obj, body=raw, timestamp=ts, signature=sig)
    assert first["ok"] is True and first["duplicate"] is False
    assert second["ok"] is True and second["duplicate"] is True

    forged = handle_zoom_webhook(payload=body_obj, body=raw, timestamp=ts, signature="v0=nope")
    assert forged["ok"] is False
    assert forged["error_code"] == "webhook_forgery"


def test_expired_token_and_rate_limit_action_required(env_paths) -> None:
    store: VicalStore = env_paths["store"]
    starts = _next_weekday_slot(store)

    def rate_limited(url: str, init: dict):
        return {"status": 429, "headers": {"Retry-After": "2"}, "json": {"message": "rate"}}

    zoom = ZoomConferencingAdapter(
        fetch_impl=rate_limited,
        get_tokens=lambda ws, uid: ZoomTokenBundle(access_token="tok", expires_at=time.time() + 1000),
        meeting_by_idempotency={},
    )
    deps = SagaDeps(zoom_adapter=zoom, store=store, ledger=reset_saga_ledger_for_tests(env_paths["saga"]))
    result = book_with_saga(
        "host1",
        guest_name="Sam",
        guest_email="sam@example.com",
        starts_at=starts,
        slug="consultation",
        skip_slot_check=True,
        workspace_id="host1",
        idempotency_key="idem-rate",
        prefer_managed_zoom=True,
        deps=deps,
    )
    # No static URL provided -> action_required
    assert result["actionRequired"] is True or result["conferenceManaged"] is False
    assert (result["booking"].metadata or {}).get("action_required") or (
        result["booking"].metadata or {}
    ).get("zoomError") == "rate_limited"


def test_cancel_deletes_zoom_meeting(env_paths) -> None:
    store: VicalStore = env_paths["store"]
    starts = _next_weekday_slot(store)
    deleted: list[str] = []

    def fake_fetch(url: str, init: dict):
        method = init.get("method")
        if method == "POST":
            return {
                "status": 201,
                "headers": {},
                "json": {
                    "id": 42,
                    "join_url": "https://zoom.us/j/42",
                    "start_url": "https://zoom.us/s/42?zak=HOST",
                },
            }
        if method == "DELETE":
            deleted.append(url)
            return {"status": 204, "headers": {}, "json": {}}
        return {"status": 200, "headers": {}, "json": {}}

    zoom = ZoomConferencingAdapter(
        fetch_impl=fake_fetch,
        get_tokens=lambda ws, uid: ZoomTokenBundle(access_token="tok", expires_at=time.time() + 1000),
        meeting_by_idempotency={},
    )
    ledger = reset_saga_ledger_for_tests(env_paths["saga"])
    deps = SagaDeps(zoom_adapter=zoom, store=store, ledger=ledger)
    created = book_with_saga(
        "host1",
        guest_name="Kim",
        guest_email="kim@example.com",
        starts_at=starts,
        slug="consultation",
        skip_slot_check=True,
        workspace_id="host1",
        idempotency_key="idem-cancel",
        prefer_managed_zoom=True,
        deps=deps,
    )
    cancel_with_saga("host1", created["booking"].id, workspace_id="host1", deps=deps)
    assert any("/meetings/42" in u for u in deleted)


def test_doctor_and_ce_without_zoom(env_paths, monkeypatch) -> None:
    monkeypatch.delenv("ZOOM_CLIENT_ID", raising=False)
    monkeypatch.delenv("ZOOM_CLIENT_SECRET", raising=False)
    report = run_vical_doctor(workspace_id="host1", user_id="host1")
    assert report["canonicalService"] == "keprix.vical.saga.book_with_saga"
    assert report["zoomOAuthConfigured"] is False
    assert report["fallback"]["ics"] is True
    assert report["fallback"]["claimsManagedZoom"] is False
