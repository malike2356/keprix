"""Tests for public/private error handling."""

from __future__ import annotations

import pytest

from keprix.errors import (
    assert_no_stack_in_public_body,
    clear_error_log_store,
    create_public_error,
    detect_five_hundred_spike,
    get_error_context,
    get_public_message,
    log_error,
    payment_error_boundary,
    public_http_payload,
    redact_value,
    search_errors,
)


@pytest.fixture(autouse=True)
def _clean():
    clear_error_log_store()
    yield
    clear_error_log_store()


def test_public_body_has_no_stack_and_links_private():
    err = Exception("ECONNREFUSED password authentication failed for role app")
    pub = create_public_error(err, status_code=500)
    assert pub["body"]["error"]["message"] == get_public_message(500)
    assert assert_no_stack_in_public_body(pub["body"])
    entry = log_error(
        err,
        {
            "route": "/api/demo",
            "method": "POST",
            "statusCode": 500,
            "requestBody": {"password": "hunter2", "token": "abc", "note": "ok"},
        },
        pub["reference"],
    )
    assert "ECONNREFUSED" in entry["message"]
    assert entry["requestBody"] == {
        "password": "[REDACTED]",
        "token": "[REDACTED]",
        "note": "ok",
    }
    assert get_error_context(pub["reference"])["errorReference"] == pub["reference"]


@pytest.mark.asyncio
async def test_payment_webhook_boundary():
    def _boom():
        raise Exception("stripe signature invalid at /opt/app/webhooks.py:44")

    result = await payment_error_boundary("stripe.webhook", _boom)
    assert result["ok"] is False
    assert assert_no_stack_in_public_body(result["body"])
    row = get_error_context(result["reference"])
    assert row["boundary"] == "payment"
    assert search_errors({"errorReference": result["reference"]})[0]["route"] == "stripe.webhook"


def test_redact_and_spike():
    assert redact_value({"Authorization": "Bearer x", "nested": {"refresh_token": "r"}}) == {
        "Authorization": "[REDACTED]",
        "nested": {"refresh_token": "[REDACTED]"},
    }
    for i in range(11):
        log_error(Exception(f"fail-{i}"), {"statusCode": 500, "route": "/api/z"})
    spike = detect_five_hundred_spike()
    assert spike["triggered"] is True


def test_fastapi_public_payload_hides_500_detail():
    body = public_http_payload(
        500,
        "internal failure near /opt/app/db.py",
        request_path="/api/x",
        method="GET",
        log_exception=Exception("internal failure near /opt/app/db.py"),
    )
    assert "/opt/app" not in str(body)
    assert "reference" in body["error"]
    assert get_error_context(body["error"]["reference"]) is not None
