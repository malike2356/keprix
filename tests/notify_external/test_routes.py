"""Notify external tests."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.notify_external.store import reset_notify_external_store
from keprix.notify_external.templates import sanitize_template_html
from keprix.notify_external.webhook_sender import WebhookTargetRejected, validate_webhook_url, verify_webhook_signature


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AUTH_ENABLED", "false")
    reset_notify_external_store()
    return TestClient(create_app())


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
