from pathlib import Path

from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


def test_ladder_routes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    assert client.get("/api/coding/ladder/mode").json()["mode"] == "full"
    assert client.put("/api/coding/ladder/mode", json={"mode": "ultra"}).json()["mode"] == "ultra"
    review = client.post("/api/coding/ladder/review", json={"diff": "+# TODO later future-proof"}).json()
    debt = client.post("/api/coding/ladder/debt", json={"text": "Simplify cache wrapper"}).json()
    metrics = client.get("/api/coding/ladder/metrics").json()

    assert review["findings"]
    assert debt["id"] == 1
    assert metrics["lines_not_written"] >= 20
