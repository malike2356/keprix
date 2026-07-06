"""Prompt 42 importer and API tests."""

from __future__ import annotations

import io
import json
import zipfile

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.backend.migration.importer import MigrationImporter, preview_manifest
from keprix.backend.migration.manifest import MigrationItem, MigrationSource, build_manifest
from keprix.backend.migration.store import reset_migration_history_store
from keprix.memory.episodic.store import create_episodic_store
from keprix.workspace.repository import workspace_repo


@pytest.fixture
def migration_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reset_migration_history_store(tmp_path / "migration")
    workspace_repo.documents.clear()
    workspace_repo.prefs.clear()
    shared_store = create_episodic_store()
    monkeypatch.setattr("keprix.backend.migration.importer.create_episodic_store", lambda: shared_store)
    return tmp_path, shared_store


def _sample_manifest(**overrides):
    items = overrides.pop("items", [
        MigrationItem(kind="memory", id="mem-0", title="Lang", content="English"),
        MigrationItem(kind="skill", id="skill-0", title="Summarize", content="body"),
        MigrationItem(kind="archive_document", id="doc-0", title="Note", content="long note"),
        MigrationItem(kind="conversation_thread", id="conv-0", title="Thread", content="user: hi"),
    ])
    manifest = build_manifest(
        source=MigrationSource(name="hermes-agent", kind="hermes"),
        items=items,
    )
    return manifest


@pytest.mark.asyncio
async def test_importer_applies_only_approved_items(migration_env):
    tmp_path, memory_store = migration_env
    manifest = _sample_manifest()
    importer = MigrationImporter()
    result = await importer.apply(manifest, ["mem-0", "doc-0"], workspace_id="default", user_id="u1")

    assert result.imported == 2
    assert result.skipped == 2
    assert result.failed == 0

    memories = await memory_store.list_all("u1")
    assert len(memories) == 1
    assert memories[0].metadata.get("tags") == ["migrated", "from:hermes"]

    docs = workspace_repo.list_documents({"id": "u1"})
    assert len(docs) == 1
    assert docs[0]["title"] == "Note"

    skills_path = tmp_path / "migration" / "skills" / "default.json"
    assert not skills_path.exists()


@pytest.mark.asyncio
async def test_importer_skill_pending_review(migration_env):
    tmp_path, _memory_store = migration_env
    manifest = _sample_manifest()
    importer = MigrationImporter()
    await importer.apply(manifest, ["skill-0"], workspace_id="default", user_id="u1")

    skills = json.loads((tmp_path / "migration" / "skills" / "default.json").read_text(encoding="utf-8"))
    assert skills[0]["status"] == "pending_review"


@pytest.mark.asyncio
async def test_conversation_thread_becomes_archive_document(migration_env):
    manifest = _sample_manifest()
    importer = MigrationImporter()
    await importer.apply(manifest, ["conv-0"], workspace_id="default", user_id="u1")
    docs = workspace_repo.list_documents({"id": "u1"})
    assert len(docs) == 1
    assert docs[0]["title"] == "Thread"


@pytest.mark.asyncio
async def test_apply_is_idempotent(migration_env):
    manifest = _sample_manifest(items=[
        MigrationItem(kind="memory", id="mem-0", title="Lang", content="English"),
    ])
    importer = MigrationImporter()
    first = await importer.apply(manifest, ["mem-0"], workspace_id="default", user_id="u1")
    second = await importer.apply(manifest, ["mem-0"], workspace_id="default", user_id="u1")
    assert first.imported == 1
    assert second.imported == 1


def test_preview_manifest_stdout(capsys):
    manifest = _sample_manifest()
    print(preview_manifest(manifest))
    captured = capsys.readouterr()
    assert "Items: 4" in captured.out
    assert "hermes" in captured.out


def _zip_export(payload: dict[str, object]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in payload.items():
            archive.writestr(name, content if isinstance(content, str) else json.dumps(content))
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_parse_endpoint_returns_manifest(migration_env):
    export = _zip_export(
        {
            "memory.json": [{"key": "Name", "value": "Ada"}],
            "skills.json": [{"name": "Code", "body": "Write code"}],
        }
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/migration/parse",
            data={"source": "hermes"},
            files={"file": ("export.zip", export, "application/zip")},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["item_count"] == 2


@pytest.mark.asyncio
async def test_parse_endpoint_422_on_bad_zip(migration_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/migration/parse",
            data={"source": "hermes"},
            files={"file": ("bad.zip", b"not-a-zip", "application/zip")},
        )
    assert response.status_code == 422
