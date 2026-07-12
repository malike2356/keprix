"""Prompt 263 client kit export/import tests."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from keprix.agent_os.action_board_store import ActionBoardStore
from keprix.agent_os.client_kit_exporter import ClientKitExporter
from keprix.agent_os.client_kit_importer import ClientKitImporter
from keprix.agent_os.headless_run_service import HeadlessRunService
from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


def _write_source_home(home: Path) -> None:
    skill = home / "skills" / "daily-brief"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Daily brief\nUses ${OPENAI_API_KEY}.\n", encoding="utf-8")
    ActionBoardStore().add_pin("default", action_type="playbook", action_id="brief", label="Brief")
    cron_dir = home / "cron"
    cron_dir.mkdir(parents=True)
    (cron_dir / "jobs.json").write_text(
        json.dumps(
            [
                {
                    "id": "job1",
                    "name": "Brief cron",
                    "prompt": "Use ${OPENAI_API_KEY}",
                    "skills": ["daily-brief"],
                    "schedule": {"kind": "interval", "minutes": 60, "display": "every 1h"},
                    "schedule_display": "every 1h",
                    "enabled": True,
                }
            ]
        ),
        encoding="utf-8",
    )
    playbook_root = home / "playbooks" / "promoted"
    playbook_root.mkdir(parents=True)
    (playbook_root / "brief.yaml").write_text(
        "id: brief\nentry: done\nsteps:\n- id: done\n  type: task\n  config:\n    set:\n      ok: true\n",
        encoding="utf-8",
    )


def test_client_kit_export_zip_contents_and_secret_names(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "source"
    monkeypatch.setenv("KEPRIX_HOME", str(home))
    _write_source_home(home)

    result = ClientKitExporter().export(name="acme", output=tmp_path / "acme.zip")

    assert result.path.exists()
    with zipfile.ZipFile(result.path) as zf:
        names = set(zf.namelist())
        assert "manifest.json" in names
        assert "action-board.json" in names
        assert "automations/cron/job1.json" in names
        assert "automations/playbooks/brief.yaml" in names
        checklist = zf.read("SECRETS_CHECKLIST.md").decode("utf-8")
    assert "OPENAI_API_KEY" in checklist
    assert "sk-" not in checklist


def test_client_kit_import_restores_pins_cron_and_playbook_then_runs(tmp_path: Path, monkeypatch) -> None:
    source_home = tmp_path / "source"
    monkeypatch.setenv("KEPRIX_HOME", str(source_home))
    _write_source_home(source_home)
    kit = ClientKitExporter().export(name="acme", output=tmp_path / "acme.zip").path

    target_home = tmp_path / "target"
    monkeypatch.setenv("KEPRIX_HOME", str(target_home))
    imported = ClientKitImporter().import_zip(kit)

    assert imported["pins"] == 1
    assert imported["cron_jobs"] == 1
    assert (target_home / "agent-os" / "action-board.json").exists()
    assert (target_home / "cron" / "jobs.json").exists()
    assert (target_home / "playbooks" / "promoted" / "brief.yaml").exists()
    result = __import__("asyncio").run(HeadlessRunService().run_playbook("brief", {"workspace_id": "default"}))
    assert result.status == "completed"


def test_client_kit_routes_export_and_admin_import(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("KEPRIX_HOME", str(home))
    monkeypatch.setenv("KEPRIX_AGENT_OS_ENABLED", "1")
    _write_source_home(home)
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "default", "role": "admin"}
    client = TestClient(app)

    preview = client.get("/api/agent-os/client-kit/preview")
    assert preview.status_code == 200
    exported = client.post("/api/agent-os/client-kit/export", json={"name": "acme"})
    assert exported.status_code == 200
    kit_path = tmp_path / "download.zip"
    kit_path.write_bytes(exported.content)
    with kit_path.open("rb") as fh:
        imported = client.post("/api/agent-os/client-kit/import", files={"file": ("kit.zip", fh, "application/zip")})
    assert imported.status_code == 200
    assert imported.json()["imported"]["pins"] == 1


def test_client_kit_import_requires_admin(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("KEPRIX_HOME", str(home))
    monkeypatch.setenv("KEPRIX_AGENT_OS_ENABLED", "1")
    _write_source_home(home)
    kit = ClientKitExporter().export(name="acme", output=tmp_path / "acme.zip").path
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    with kit.open("rb") as fh:
        response = client.post("/api/agent-os/client-kit/import", files={"file": ("kit.zip", fh, "application/zip")})
    assert response.status_code == 403
