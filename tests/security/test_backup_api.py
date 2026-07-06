"""Backup route tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.security.rate_limiter import reset_rate_limits
from keprix.workspace.backup_service import BackupService


@pytest.fixture
def backup_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    reset_rate_limits()
    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)
    service = BackupService(str(tmp_path / "backups"))
    monkeypatch.setattr("keprix.workspace.backup_routes.backup_service", service)
    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    client.headers.update({"Authorization": f"Bearer {login.json()['token']}"})
    return client, tmp_path, service


def test_create_and_restore_backup(backup_client):
    client, tmp_path, service = backup_client
    marker = tmp_path / "auth.json"
    marker.write_text('{"marker": true}', encoding="utf-8")

    created = client.post("/api/admin/backup/create", json={})
    assert created.status_code == 200
    backup_id = created.json()["id"]

    marker.write_text('{"marker": false}', encoding="utf-8")

    path = service.get_backup_path(backup_id)
    assert path is not None
    archive_bytes = path.read_bytes()
    restored = service.restore_backup(archive_bytes)
    assert restored["ok"] is True
    assert '"marker": true' in marker.read_text(encoding="utf-8")

    download = client.get(f"/api/admin/backup/{backup_id}/download")
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/gzip"


def test_restore_requires_confirm(backup_client):
    client, tmp_path, service = backup_client
    created = client.post("/api/admin/backup/create", json={})
    backup_id = created.json()["id"]
    path = service.get_backup_path(backup_id)
    assert path is not None

    with path.open("rb") as handle:
        denied = client.post(
            "/api/admin/backup/restore",
            data={"confirm": "false"},
            files={"file": ("backup.tar.gz", handle.read(), "application/gzip")},
        )
    assert denied.status_code == 422

