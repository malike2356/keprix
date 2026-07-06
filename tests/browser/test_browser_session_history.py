"""Browser session history API tests (Prompt 196)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.browser.browser_profile import ProfileKind, get_profile_store
from keprix.browser.harness import get_harness_manager


@pytest.mark.asyncio
async def test_session_list_returns_recent_dry_run(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_API_TOKEN", "test-api-token")
    headers = {"Authorization": "Bearer test-api-token"}
    workspace_id = "browser-history-test"

    profile = get_profile_store().create(
        workspace_id=workspace_id,
        name="history-disposable",
        kind=ProfileKind.DISPOSABLE,
    )
    harness, record = get_harness_manager().open_session(
        workspace_id=workspace_id,
        objective="List dry run sessions",
        profile_id=profile.id,
    )
    harness.engine.run_action(harness.session_id, action="fill", selector="card", value="4111")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        listed = await client.get(
            f"/api/browser/sessions?workspace_id={workspace_id}",
            headers=headers,
        )
        assert listed.status_code == 200
        sessions = listed.json()["sessions"]
        assert any(row["session_id"] == record.session_id for row in sessions)
        match = next(row for row in sessions if row["session_id"] == record.session_id)
        assert match["mode"] == "dry_run"
        assert match["step_count"] >= 1

        steps_resp = await client.get(
            f"/api/browser/sessions/{record.session_id}/steps",
            headers=headers,
        )
    assert steps_resp.status_code == 200
    body = steps_resp.json()
    assert body["mode"] == "dry_run"
    assert len(body["steps"]) >= 1
