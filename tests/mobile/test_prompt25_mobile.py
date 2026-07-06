"""Prompt 25 mobile companion and push tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.backend.notifications.push import reset_push_services
from keprix.mobile.companion.pairing import get_companion_store, reset_companion_store


@pytest.fixture
def mobile_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AUTH_ENABLED", "false")
    reset_companion_store()
    reset_push_services()
    return tmp_path


@pytest.mark.asyncio
async def test_companion_pair_returns_qr_payload(mobile_env) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/companion/pair?workspace_id=default")
    assert response.status_code == 200
    body = response.json()
    assert body["pairing_id"]
    assert body["code"]
    assert body["qr_payload"]["server_url"]


@pytest.mark.asyncio
async def test_companion_pair_confirm_issues_token(mobile_env) -> None:
    store = get_companion_store()
    pairing = store.create_pairing("default", created_by="admin")
    result = store.confirm_pairing(
        str(pairing["pairing_id"]),
        code=str(pairing["code"]),
        device_name="Test Phone",
        platform="ios",
    )
    assert result is not None
    assert result["token"].startswith("kp_")


@pytest.mark.asyncio
async def test_push_register_and_send(mobile_env) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        register = await client.post(
            "/api/notifications/register",
            json={"platform": "ios", "token": "apns-token-12345678", "workspace_id": "default"},
        )
        assert register.status_code == 200
        send = await client.post(
            "/api/notifications/send",
            json={"title": "Job complete", "message": "Export finished", "workspace_id": "default"},
        )
    assert send.status_code == 200
    assert send.json()["count"] == 1


def test_ios_carina_files_exist() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    assert (root / "mobile/ios/Sources/CarinaApp.swift").exists()
    assert (root / "mobile/ios/Sources/CarinaOnboardingView.swift").exists()
    assert (root / "mobile/ios/Sources/CarinaServerConfig.swift").exists()


def test_android_application_id() -> None:
    from pathlib import Path

    gradle = Path(__file__).resolve().parents[2] / "mobile/android/app/build.gradle.kts"
    text = gradle.read_text(encoding="utf-8")
    assert 'applicationId = "com.verlox.carinakeprix"' in text
    assert (Path(__file__).resolve().parents[2] / "mobile/android/app/src/main/java/com/verlox/carinakeprix/app/CarinaOnboardingActivity.kt").exists()
