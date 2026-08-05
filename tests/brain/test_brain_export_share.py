from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from keprix.brain.export_csv import export_brain_edges_csv, export_brain_nodes_csv
from keprix.brain.export_json import export_brain_json
from keprix.brain.export_obsidian import export_brain_obsidian
from keprix.brain.share_links import share_link_store
from keprix.data_architecture.graph_edges import add_graph_edge


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))


@pytest.mark.asyncio
async def test_export_json_csv_obsidian() -> None:
    workspace_id = "export-workspace"
    add_graph_edge(
        workspace_id=workspace_id,
        source_kind="memory",
        source_id="mem-1",
        target_kind="skill",
        target_id="skill-1",
        relation="used_in",
    )

    payload = await export_brain_json(workspace_id)
    assert payload["format"] == "keprix-brain-export"
    assert payload["stats"]["total_nodes"] >= 2
    assert payload["stats"]["nodes_by_kind"]["memory"] >= 1

    nodes_csv = await export_brain_nodes_csv(workspace_id)
    assert "id,kind,label,summary,created_at,edge_count,relation_types" in nodes_csv
    assert "mem-1" in nodes_csv

    edges_csv = await export_brain_edges_csv(workspace_id)
    assert "edge_id,source_kind,source_id" in edges_csv
    assert "used_in" in edges_csv

    archive = await export_brain_obsidian(workspace_id)
    with zipfile.ZipFile(BytesIO(archive)) as zf:
        names = zf.namelist()
        assert any(name.endswith(".md") for name in names)


def test_export_and_share_routes() -> None:
    from fastapi.testclient import TestClient

    from keprix.api.server import create_app
    from keprix.auth.dependencies import get_current_user

    workspace_id = "route-export-share"
    add_graph_edge(
        workspace_id=workspace_id,
        source_kind="memory",
        source_id="mem-route",
        target_kind="session",
        target_id="sess-route",
        relation="derived_from",
    )
    app = create_app()
    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "u1",
        "role": "user",
        "workspace_id": workspace_id,
    }

    json_response = client.get(f"/api/brain/export/json?workspace_id={workspace_id}")
    assert json_response.status_code == 200
    assert "attachment" in json_response.headers.get("content-disposition", "")
    body = json.loads(json_response.text)
    assert body["workspace_id"] == workspace_id

    obsidian_response = client.get(f"/api/brain/export/obsidian?workspace_id={workspace_id}")
    assert obsidian_response.status_code == 200
    assert obsidian_response.headers["content-type"] == "application/zip"

    csv_response = client.get(f"/api/brain/export/csv?workspace_id={workspace_id}")
    assert csv_response.status_code == 200
    assert "mem-route" in csv_response.text

    create = client.post(
        f"/api/brain/share?workspace_id={workspace_id}",
        json={"expires_in_days": 7, "scope": "all", "password": "secret"},
    )
    assert create.status_code == 200
    share_id = create.json()["share_id"]
    assert share_id
    assert "/brain/share/" in create.json()["url"]

    stats = client.get(f"/api/brain/share/{share_id}/stats?workspace_id={workspace_id}")
    assert stats.status_code == 200
    assert stats.json()["access_count"] == 0

    denied = client.get(f"/api/brain/share/{share_id}/data")
    assert denied.status_code == 401

    allowed = client.get(f"/api/brain/share/{share_id}/data?password=secret")
    assert allowed.status_code == 200
    shared = allowed.json()
    assert "workspace_id" not in shared
    assert shared["total_nodes"] >= 2
    assert shared["password_protected"] is True

    node = client.get(f"/api/brain/share/{share_id}/node/memory/mem-route?password=secret")
    assert node.status_code == 200
    assert node.json()["id"] == "mem-route"

    second = client.get(f"/api/brain/share/{share_id}/data?password=secret")
    assert second.status_code == 200
    updated = share_link_store.get(share_id)
    assert updated is not None
    assert updated.access_count >= 2

    revoke = client.delete(f"/api/brain/share/{share_id}?workspace_id={workspace_id}")
    assert revoke.status_code == 200
    gone = client.get(f"/api/brain/share/{share_id}/data?password=secret")
    assert gone.status_code == 404
