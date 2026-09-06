from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.auth import dependencies as deps
from keprix.workspace import deletion
from keprix.workspace.routes.deletion_routes import router


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    store = deletion.WorkspaceDeletionStore(tmp_path / "deletions.json")
    monkeypatch.setattr(deletion, "_store", store)
    async def cancel_subscription(*_args, **_kwargs):
        return None

    monkeypatch.setattr(deletion, "cancel_subscription", cancel_subscription)
    app = FastAPI()
    app.include_router(router)

    async def user() -> dict[str, str]:
        return {"id": "owner-1"}

    app.dependency_overrides[deps.get_current_user] = user
    return TestClient(app)


def test_owner_has_grace_and_can_cancel(client: TestClient) -> None:
    requested = client.post("/api/workspace/deletion/request", params={"workspace_id": "owner-1"})
    assert requested.status_code == 200
    assert requested.json()["state"] == "pending_deletion"
    assert requested.json()["seconds_remaining"] > 71 * 3600
    cancelled = client.post("/api/workspace/deletion/cancel", params={"workspace_id": "owner-1"})
    assert cancelled.status_code == 200
    assert cancelled.json()["state"] == "active"


def test_cross_workspace_deletion_is_denied(client: TestClient) -> None:
    response = client.post("/api/workspace/deletion/request", params={"workspace_id": "other"})
    assert response.status_code == 403


def test_due_purge_requires_callback_and_records_completion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = deletion.WorkspaceDeletionStore(tmp_path / "deletions.json")
    monkeypatch.setattr(deletion, "_store", store)
    row = {"workspace_id": "ws", "purge_after": "2000-01-01T00:00:00+00:00", "audit_events": []}
    store.save("ws", row)
    with pytest.raises(ValueError):
        deletion.purge_due()
    deleted: list[str] = []
    assert deletion.purge_due(purge_workspace=deleted.append) == ["ws"]
    assert deleted == ["ws"]
    assert store.get("ws")["audit_events"][-1]["event"] == "workspace_deletion_purged"
