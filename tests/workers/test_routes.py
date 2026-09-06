from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.auth import dependencies as deps
from keprix.workers.routes import router
from keprix.workers.store import WorkerStore


def test_worker_is_workspace_scoped_and_token_is_hashed(tmp_path: Path, monkeypatch) -> None:
    store = WorkerStore(tmp_path / "workers.json")
    monkeypatch.setattr("keprix.workers.routes.get_worker_store", lambda: store)
    app = FastAPI()
    app.include_router(router)

    async def user() -> dict[str, str]:
        return {"id": "u"}

    app.dependency_overrides[deps.get_current_user] = user
    client = TestClient(app)
    created = client.post("/api/workers", json={"workspace_id": "a", "slug": "coder", "persona": "CODEX"})
    assert created.status_code == 201
    worker_id = created.json()["worker"]["id"]
    connected = client.post(f"/api/workers/{worker_id}/telegram", json={"workspace_id": "a", "token": "x" * 24, "chat_id": "1"})
    assert connected.status_code == 200
    assert "token" not in connected.text
    assert client.get("/api/workers", params={"workspace_id": "b"}).json()["count"] == 0
    assert client.post(f"/api/workers/{worker_id}/preferred", params={"workspace_id": "a"}).status_code == 200
    saved = client.post(f"/api/workers/{worker_id}/task", json={"workspace_id": "a", "task": {"step": "resume"}})
    assert saved.status_code == 200
    assert client.get(f"/api/workers/{worker_id}/task", params={"workspace_id": "a"}).json()["can_resume"] is True
    approval = client.post(f"/api/workers/{worker_id}/approvals", json={"workspace_id": "a", "action": "send_email"})
    assert approval.status_code == 200
    assert approval.json()["approval"]["worker_slug"] == "coder"
