"""Legal acceptance tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app


@pytest.mark.asyncio
async def test_legal_gate_and_acceptance(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("KEPRIX_API_TOKEN", "test-api-token")
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_LEGAL_GATE", "1")
    import keprix.legal.store as legal_store_module

    legal_store_module._store = None
    headers = {
        "Authorization": "Bearer test-api-token",
        "x-user-id": "user-legal-test",
        "x-workspace-id": "ws-legal-test",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        blocked = await client.get("/api/privacy/consent", headers=headers)
        assert blocked.status_code == 451
        pending = blocked.json()["pending_policies"]
        assert "terms_of_use" in pending

        policies = await client.get("/api/legal/policies")
        assert policies.status_code == 200
        policy_types = [row["policy_type"] for row in policies.json()["policies"]]
        accepted = await client.post(
            "/api/legal/accept",
            headers=headers,
            json={"policy_types": policy_types},
        )
        assert accepted.status_code == 200
        assert accepted.json()["all_accepted"] is True

        allowed = await client.get("/api/privacy/consent", headers=headers)
        assert allowed.status_code == 200
