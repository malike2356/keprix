"""Review token tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from keprix.review_gateway.tokens import generate_review_token, validate_review_token


def test_generate_and_validate_token() -> None:
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    token_id, url_token = generate_review_token("req-1", "default", expires)
    assert token_id
    assert url_token
    assert validate_review_token(
        url_token,
        token_id=token_id,
        review_request_id="req-1",
        workspace_id="default",
        expires_at=expires,
        status="pending",
    )


def test_invalid_token_rejected() -> None:
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    token_id, url_token = generate_review_token("req-1", "default", expires)
    assert not validate_review_token(
        url_token,
        token_id=token_id,
        review_request_id="req-2",
        workspace_id="default",
        expires_at=expires,
        status="pending",
    )
