from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user
from keprix.data_architecture.graph_edges import add_graph_edge


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))


def test_brain_graph_routes_require_auth_and_return_graph() -> None:
    workspace_id = "route-workspace"
    add_graph_edge(
        workspace_id=workspace_id,
        source_kind="tool",
        source_id="calendar_book",
        target_kind="session",
        target_id="sess-1",
        relation="used_in",
    )
    app = create_app()
    client = TestClient(app)

    unauthenticated = client.get(f"/api/brain/graph?workspace_id={workspace_id}")
    assert unauthenticated.status_code in {401, 403}

    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user", "workspace_id": workspace_id}
    authenticated = client.get(f"/api/brain/graph?workspace_id={workspace_id}")
    node = client.get(f"/api/brain/graph/node/tool/calendar_book?workspace_id={workspace_id}")
    neighbours = client.get(f"/api/brain/graph/neighbours/tool/calendar_book?workspace_id={workspace_id}")
    depth = client.get(f"/api/brain/graph/neighbours/tool/calendar_book?workspace_id={workspace_id}&depth=2")
    search = client.get(f"/api/brain/graph/search?workspace_id={workspace_id}&q=calendar")
    stats = client.get(f"/api/brain/graph/stats?workspace_id={workspace_id}")
    denied = client.get("/api/brain/graph?workspace_id=other-workspace")
    deleted = client.delete(f"/api/brain/graph/edges?workspace_id={workspace_id}&source_kind=tool&source_id=calendar_book")

    assert authenticated.status_code == 200
    assert authenticated.json()["total_nodes"] == 2
    assert node.status_code == 200
    assert node.json()["content"]["id"] == "calendar_book"
    assert neighbours.json()["total_edges"] == 1
    assert depth.status_code == 200
    assert search.status_code == 200
    assert search.json()["matches"][0]["id"] == "calendar_book"
    assert stats.json()["edges_by_relation"]["used_in"] == 1
    assert denied.status_code == 403
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] == 1
