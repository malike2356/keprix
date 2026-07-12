"""Prompt 270 Phase 5 polish: playbook, guardrails, deploy assets, error paste."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from keprix.agent_apps.catalog import list_catalog_templates, template_dir
from keprix.agent_apps.local_runner import run_local
from keprix.agent_os.guardrails import backup_vault, default_workspace_root, guardrails_status
from keprix.agent_os.token_playbook import TECHNIQUES, playbook_status
from keprix.agent_os.workflows.error_paste import analyze_error_paste
from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user
from keprix.vault.config import VaultConfig, save_vault_config


@pytest.fixture
def keprix_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / ".keprix"
    home.mkdir()
    monkeypatch.setenv("KEPRIX_HOME", str(home))
    monkeypatch.setenv("KEPRIX_AGENT_OS_ENABLED", "1")
    monkeypatch.setenv("KEPRIX_GUARDRAILS_DEFAULT", "true")
    monkeypatch.setenv("KEPRIX_VAULT_AUTO_BACKUP", "true")
    return home


def test_token_playbook_has_ten_techniques() -> None:
    assert len(TECHNIQUES) == 10
    status = playbook_status()
    assert status["technique_count"] == 10
    assert "Token Minimization Playbook" in status["markdown"]
    assert all("id" in item and "title" in item for item in status["techniques"])


def test_guardrails_workspace_and_backup(keprix_home: Path) -> None:
    workspace = default_workspace_root()
    assert workspace.is_dir()
    assert str(keprix_home) in str(workspace)

    vault = keprix_home / "vault"
    vault.mkdir()
    (vault / "note.md").write_text("# hello\n", encoding="utf-8")
    save_vault_config(
        VaultConfig(
            provider="local_folder",
            root_path=str(vault),
        )
    )

    status = guardrails_status()
    assert status["enabled"] is True
    assert status["vault_auto_backup"] is True
    assert status["approvals_required"] is True

    snap = backup_vault(reason="test")
    assert snap["ok"] is True
    assert Path(snap["path"]).is_file()
    assert Path(snap["path"]).stat().st_size > 0


def test_error_paste_classifies_module_missing() -> None:
    result = analyze_error_paste(error_text="ModuleNotFoundError: No module named foo")
    assert result["status"] == "ok"
    assert result["workflow"] == "error-paste"
    assert result["classification"] == "Missing Python dependency"
    assert "Fix plan" in result["output"]
    assert result["artifact"]["auto_skill"] is True


def test_error_paste_catalog_app(keprix_home: Path) -> None:
    ids = {item["id"] for item in list_catalog_templates()}
    assert "error-paste" in ids
    app_dir = template_dir("error-paste")
    assert app_dir is not None
    run = run_local(
        app_dir,
        input_text="Permission denied: /etc/shadow",
        context={"form": {"error_text": "Permission denied: /etc/shadow"}},
    )
    assert run["result"]["status"] == "ok"
    assert "Permission" in run["result"]["classification"]


def test_phase5_api_routes(keprix_home: Path) -> None:
    vault = keprix_home / "vault"
    vault.mkdir()
    (vault / "a.md").write_text("x\n", encoding="utf-8")
    save_vault_config(
        VaultConfig(
            provider="local_folder",
            root_path=str(vault),
        )
    )

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    playbook = client.get("/api/agent-os/token-playbook")
    assert playbook.status_code == 200
    assert playbook.json()["technique_count"] == 10

    guardrails = client.get("/api/agent-os/guardrails")
    assert guardrails.status_code == 200
    assert guardrails.json()["ok"] is True

    backup = client.post("/api/agent-os/guardrails/backup-vault")
    assert backup.status_code == 200
    assert backup.json()["ok"] is True

    paste = client.post(
        "/api/agent-os/error-paste",
        json={"error_text": "Connection refused to 127.0.0.1:3333"},
    )
    assert paste.status_code == 200
    body = paste.json()
    assert body["status"] == "ok"
    assert "connectivity" in body["classification"].lower() or "Service" in body["classification"]


def test_deploy_assets_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    assert (root / "scripts" / "deploy-server.sh").is_file()
    assert (root / "scripts" / "deploy-managed.sh").is_file()
    assert (root / "deploy" / "keprix.service").is_file()
    assert (root / "fly.toml").is_file()
    assert (root / "docker" / "Dockerfile.backend").is_file()
    unit = (root / "deploy" / "keprix.service").read_text(encoding="utf-8")
    assert "@KEPRIX_ROOT@" in unit
    assert "127.0.0.1" in unit
    assert "uvicorn keprix.api.main:app" in unit
