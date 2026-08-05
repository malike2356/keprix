"""Prompt 272 vault pack API route tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


def test_vault_pack_routes_list_init_and_validate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    packs = client.get("/api/vault/packs")
    assert packs.status_code == 200
    assert any(pack["id"] == "obsidian-starter" for pack in packs.json()["packs"])

    vault = tmp_path / "vault"
    initialized = client.post("/api/vault/init", json={"pack": "obsidian-starter", "path": str(vault)})
    assert initialized.status_code == 200
    assert (vault / "KEPRIX.md").is_file()

    validated = client.post("/api/vault/validate", json={"path": str(vault)})
    assert validated.status_code == 200
    assert validated.json()["ok"] is True
