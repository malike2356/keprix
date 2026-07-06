"""Prompt 29 project builder tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.backend.builder.store import reset_builder_store
from keprix.backend.builder.registry import get_project_registry


@pytest.fixture
def builder_env(tmp_path, monkeypatch):
    root = tmp_path / "verlox"
    sample = root / "sample-app"
    sample.mkdir(parents=True)
    (sample / "package.json").write_text(
        json.dumps({"name": "sample-app", "dependencies": {"next": "14.0.0"}}),
        encoding="utf-8",
    )
    (sample / "README.md").write_text("# sample\n", encoding="utf-8")

    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("BUILDER_ROOT", str(root))
    monkeypatch.setenv("AUTH_ENABLED", "false")
    reset_builder_store()
    import keprix.backend.builder.registry as registry_module

    registry_module._registry = None
    return tmp_path


@pytest.mark.asyncio
async def test_list_projects_discovers_scan_root(builder_env) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/builder/projects/scan")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
    project = payload["projects"][0]
    assert "stack_type" in project
    assert isinstance(project["tech_stack"], list)


@pytest.mark.asyncio
async def test_scaffold_keprix_nextjs_fleetx(builder_env, tmp_path) -> None:
    target = tmp_path / "scaffolds"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/builder/scaffold",
            json={
                "template": "keprix-nextjs-app",
                "name": "fleetx",
                "path": str(target),
            },
        )
    assert response.status_code == 200
    result = response.json()["result"]
    project_path = Path(result["path"])
    domains = (project_path / "src" / "keprix" / "domains.ts").read_text(encoding="utf-8")
    assert "Vehicle" in domains
    assert "Driver" in domains
    assert "Trip" in domains
    assert (project_path / "package.json").exists()
    assert (project_path / "src" / "keprix" / "client.ts").exists()


@pytest.mark.asyncio
async def test_build_job_creates_and_streams(builder_env, monkeypatch) -> None:
    registry = get_project_registry()
    projects = registry.scan()
    project_id = projects[0]["id"]

    def _fake_run(job_id: str) -> None:
        from keprix.backend.builder.store import get_builder_store

        store = get_builder_store()
        store.update_job(job_id, {"status": "running"})
        store.append_job_log(job_id, "[builder] simulated build")
        store.update_job(job_id, {"status": "done", "diff_summary": "file README.md"})

    monkeypatch.setattr("keprix.backend.builder.routes.start_build_job", _fake_run)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create = await client.post(
            f"/api/builder/projects/{project_id}/build",
            json={"instruction": "add user export CSV feature"},
        )
        assert create.status_code == 200
        job_id = create.json()["job"]["id"]
        _fake_run(job_id)

        job = await client.get(f"/api/builder/jobs/{job_id}")
        assert job.status_code == 200
        assert "simulated build" in job.json()["log"]

        stream = await client.get(f"/api/builder/jobs/{job_id}/stream")
        assert stream.status_code == 200
        assert "text/event-stream" in stream.headers.get("content-type", "")


def test_cli_builder_list(builder_env, capsys) -> None:
    from keprix.keprix_cli.builder_commands import cmd_builder_list

    class Args:
        pass

    get_project_registry().scan()
    code = cmd_builder_list(Args())
    captured = capsys.readouterr().out
    assert code == 0
    payload = json.loads(captured)
    assert len(payload["projects"]) >= 1
