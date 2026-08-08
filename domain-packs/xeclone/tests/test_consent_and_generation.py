"""Consent and generation boundary tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PACK_ROOT = Path(__file__).resolve().parents[1]


def _client() -> TestClient:
    if str(PACK_ROOT) not in sys.path:
        sys.path.insert(0, str(PACK_ROOT))
    import http_app
    from consent.ledger import reset_ledger
    from assets.registry import reset_assets
    from tools.handlers import reset_handler_flags, last_generation_called_distribution

    reset_ledger()
    reset_assets()
    reset_handler_flags()
    return TestClient(http_app.app), last_generation_called_distribution


def test_revoked_consent_blocks_generation() -> None:
    client, _ = _client()
    reg = client.post(
        "/v1/products/xeclone/assets/register",
        json={
            "asset_id": "voice-1",
            "media_type": "audio",
            "grant_purposes": ["generate", "upload_to_provider"],
        },
    )
    assert reg.status_code == 200
    revoke = client.post(
        "/v1/products/xeclone/assets/voice-1/revoke-consent",
        json={"purpose": "generate"},
    )
    assert revoke.status_code == 200
    # After revoke, consent-gated voice synth falls back or errors; either blocks real generation
    inv = client.post(
        "/v1/products/xeclone/invoke",
        json={
            "capability": "voice_synthesise",
            "input": {"asset_id": "voice-1", "script": "hello", "subject_id": "owner-laud"},
        },
    )
    body = inv.json()
    # Handler returns 200 with fallback_text_only or 400 consent_denied
    if inv.status_code == 200:
        assert body["result"].get("fallback_text_only") is True or body["result"].get("error_original") == "consent_denied"
    else:
        assert "consent" in str(body).lower()


def test_other_person_media_rejected() -> None:
    client, _ = _client()
    client.post(
        "/v1/products/xeclone/assets/register",
        json={
            "asset_id": "other-face",
            "media_type": "image",
            "subject_id": "someone-else",
            "grant_purposes": ["generate"],
        },
    )
    inv = client.post(
        "/v1/products/xeclone/invoke",
        json={
            "capability": "likeness_image_generate",
            "input": {
                "asset_id": "other-face",
                "subject_id": "someone-else",
                "prompt": "impersonate",
            },
        },
    )
    assert inv.status_code == 400
    assert "other_person" in str(inv.json()).lower() or "rejected" in str(inv.json()).lower()


def test_generation_cannot_call_distribution() -> None:
    client, last_flag = _client()
    inv = client.post(
        "/v1/products/xeclone/invoke",
        json={
            "capability": "post_draft",
            "input": {"topic": "hello", "_call_distribution": True},
        },
    )
    assert inv.status_code == 400
    assert last_flag() is True or "distribution" in str(inv.json()).lower()
    # Successful generation without the flag must not invoke distribution
    ok = client.post(
        "/v1/products/xeclone/invoke",
        json={"capability": "post_draft", "input": {"topic": "hello"}},
    )
    assert ok.status_code == 200
    assert ok.json()["result"]["distribution_invoked"] is False
