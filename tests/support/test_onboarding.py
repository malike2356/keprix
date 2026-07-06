"""Support onboarding checklist tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.support.onboarding import default_checklist, update_checklist_item
from keprix.support.store import SupportStore


@pytest.fixture()
def support_store(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_API_TOKEN", "test-api-token")
    import keprix.support.store as store_module

    store = SupportStore(base_dir=tmp_path / "support")
    store_module._store = store
    return store


def test_onboarding_checklist_updates(support_store) -> None:
    items = default_checklist()
    assert items
    updated = update_checklist_item("admin-password", completed=True)
    match = next(item for item in updated if item["id"] == "admin-password")
    assert match["completed"] is True


@pytest.mark.asyncio
async def test_checklist_route(support_store) -> None:
    headers = {"Authorization": "Bearer test-api-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        listed = await client.get("/api/support/onboarding/checklist", headers=headers)
        assert listed.status_code == 200
        assert listed.json()["items"]
        patched = await client.patch(
            "/api/support/onboarding/checklist",
            headers=headers,
            json={"item_id": "llm-provider", "completed": True},
        )
        assert patched.status_code == 200
        assert patched.json()["progress"]["completed"] >= 1
