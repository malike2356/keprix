from pathlib import Path

from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


def test_skill_run_compatibility_routes(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / ".keprix"
    monkeypatch.setenv("KEPRIX_HOME", str(home))
    monkeypatch.setenv("KEPRIX_AGENT_OS_ENABLED", "1")
    skill = home / "skills" / "daily-brief"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Daily brief\n\nSummarize the morning.\n", encoding="utf-8")
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    run = client.post("/api/skills/daily-brief/run", json={"params": {"workspace_id": "default"}})
    history = client.get("/api/skills/daily-brief/runs")

    assert run.status_code == 200
    assert run.json()["skill"] == "daily-brief"
    assert run.json()["status"] == "completed"
    assert run.json()["tokens_used"] > 0
    assert history.status_code == 200
    assert history.json()["runs"][0]["source_id"] == "daily-brief"
