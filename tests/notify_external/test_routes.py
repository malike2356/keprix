"""Notify external tests."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.notify_external.store import get_notify_external_store, reset_notify_external_store
from keprix.notify_external.templates import sanitize_template_html
from keprix.notify_external.webhook_sender import WebhookTargetRejected, validate_webhook_url, verify_webhook_signature


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AUTH_ENABLED", "false")
    reset_notify_external_store()
    app = create_app()
    # create_app reloads project .env (AUTH_ENABLED=true); force off for route tests.
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setattr("keprix.auth.config.auth_enabled", lambda: False)
    monkeypatch.setattr("keprix.auth.dependencies.auth_enabled", lambda: False)
    return TestClient(app)


def test_reject_http_webhook() -> None:
    with pytest.raises(WebhookTargetRejected):
        validate_webhook_url("http://example.com/hook")


def test_reject_localhost_webhook() -> None:
    with pytest.raises(WebhookTargetRejected):
        validate_webhook_url("https://localhost/hook")


def test_webhook_signature_roundtrip() -> None:
    payload = b'{"ok":true}'
    secret = b"test-secret"
    signature = __import__("hmac").new(secret, payload, __import__("hashlib").sha256).hexdigest()
    assert verify_webhook_signature(payload, secret, f"sha256={signature}")


def test_template_script_rejected() -> None:
    with pytest.raises(ValueError):
        sanitize_template_html('<script>alert(1)</script>')


def test_get_config_masks_password(client) -> None:
    response = client.get("/api/notify-external/config")
    assert response.status_code == 200
    body = response.json()
    assert "smtp_password" not in body


def test_send_webhook_rejects_http(client) -> None:
    response = client.post(
        "/api/notify-external/send",
        json={
            "channel": "webhook",
            "recipient_address": "http://example.com/hook",
            "webhook_payload": {"hello": "world"},
        },
    )
    assert response.status_code == 422


def test_list_templates(client) -> None:
    response = client.get("/api/notify-external/templates")
    assert response.status_code == 200
    names = {row["name"] for row in response.json()["templates"]}
    assert "review_request" in names
    assert "pack_gate_pending" in names


def test_test_email_returns_notification_id(client, monkeypatch) -> None:
    store = get_notify_external_store()
    store.save_config(
        "default",
        {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "user",
            "smtp_from_email": "noreply@example.com",
        },
    )

    async def _resolve(cfg):
        return "secret"

    monkeypatch.setattr("keprix.notify_external.smtp_sender._resolve_smtp_password", _resolve)
    monkeypatch.setattr("keprix.notify_external.smtp_sender._send_smtp_sync", lambda *a, **k: None)

    response = client.post("/api/notify-external/test-email", json={"to_email": "ops@example.com"})
    assert response.status_code == 200
    body = response.json()
    assert body["notification_id"]
    assert body["status"] == "sent"
    row = store.get_notification(body["notification_id"])
    assert row is not None
    assert row["status"] == "sent"


def test_send_email_records_sent_with_mocked_smtp(client, monkeypatch) -> None:
    store = get_notify_external_store()
    store.save_config(
        "default",
        {
            "smtp_host": "smtp.example.com",
            "smtp_username": "user",
            "smtp_from_email": "noreply@example.com",
        },
    )

    async def _resolve(cfg):
        return "secret"

    monkeypatch.setattr("keprix.notify_external.smtp_sender._resolve_smtp_password", _resolve)
    monkeypatch.setattr("keprix.notify_external.smtp_sender._send_smtp_sync", lambda *a, **k: None)

    response = client.post(
        "/api/notify-external/send",
        json={
            "channel": "email",
            "recipient_address": "auditor@example.com",
            "subject": "Hello",
            "body_text": "World",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "sent"


def test_rate_limit_returns_429(client, monkeypatch) -> None:
    store = get_notify_external_store()
    monkeypatch.setattr(store, "check_rate_limit", lambda *a, **k: False)
    response = client.post(
        "/api/notify-external/send",
        json={
            "channel": "email",
            "recipient_address": "auditor@example.com",
            "subject": "Hello",
            "body_text": "World",
        },
    )
    assert response.status_code == 429


def test_retry_failed_notification(client, monkeypatch) -> None:
    store = get_notify_external_store()
    store.save_config("default", {"smtp_host": "smtp.example.com", "max_retries": 3})
    row = store.create_notification(
        "default",
        {
            "channel": "email",
            "recipient_address": "ops@example.com",
            "subject": "Retry me",
            "body_text": "please",
            "status": "failed",
            "attempts": 1,
            "last_attempted_at": "2000-01-01T00:00:00+00:00",
        },
    )
    # create_notification overwrites status to pending by default via fields merge
    store.update_notification(row["id"], {"status": "failed", "attempts": 1})

    async def _resolve(cfg):
        return "secret"

    monkeypatch.setattr("keprix.notify_external.smtp_sender._resolve_smtp_password", _resolve)
    monkeypatch.setattr("keprix.notify_external.smtp_sender._send_smtp_sync", lambda *a, **k: None)

    response = client.post(f"/api/notify-external/notifications/{row['id']}/retry")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "sent"
    assert body["retried"] is True
