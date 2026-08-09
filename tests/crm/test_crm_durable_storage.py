"""Prompt 622: durable CRM storage (SQLite + optional Postgres)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from keprix.crm.store import ConflictError, CrmStore, reset_crm_store_for_tests


@pytest.fixture()
def sqlite_store(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("KEPRIX_CRM_BACKEND", "sqlite")
    monkeypatch.delenv("KEPRIX_CRM_FORCE_PG", raising=False)
    path = tmp_path / "crm.sqlite"
    return reset_crm_store_for_tests(path)


def test_sqlite_restart_persistence(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_CRM_BACKEND", "sqlite")
    path = tmp_path / "persist.sqlite"
    store = CrmStore(path=path)
    lead = store.create_lead("ws_a", name="Persist Me", email="p@example.com")
    lead_id = lead["id"]
    store.close()

    again = CrmStore(path=path)
    found = again.get_lead("ws_a", lead_id)
    assert found is not None
    assert found["name"] == "Persist Me"
    again.close()


def test_sqlite_workspace_isolation(sqlite_store) -> None:
    lead = sqlite_store.create_lead("ws_a", name="Only A", email="a@example.com")
    assert sqlite_store.get_lead("ws_b", lead["id"]) is None
    assert sqlite_store.list_leads("ws_b") == []
    assert sqlite_store.get_lead("ws_a", lead["id"])["name"] == "Only A"


def test_idempotency_no_double_insert(sqlite_store) -> None:
    first = sqlite_store.remember_idempotency(
        "ws_a",
        scope="delivery",
        idempotency_key="evt-1",
        result={"ok": True},
    )
    second = sqlite_store.remember_idempotency(
        "ws_a",
        scope="delivery",
        idempotency_key="evt-1",
        result={"ok": True, "again": 1},
    )
    assert first["id"] == second["id"]
    rows = sqlite_store._fetchall(
        "SELECT * FROM crm_idempotency WHERE workspace_id = ? AND scope = ?",
        ("ws_a", "delivery"),
    )
    assert len(rows) == 1


def test_version_conflict_raises(sqlite_store) -> None:
    lead = sqlite_store.create_lead("ws_a", name="V", email="v@example.com")
    sqlite_store.update_lead("ws_a", lead["id"], name="V2", expected_version=1)
    with pytest.raises(ConflictError):
        sqlite_store.update_lead("ws_a", lead["id"], name="V3", expected_version=1)


def _pg_url() -> str:
    return (
        os.environ.get("KEPRIX_TEST_DATABASE_URL")
        or "postgresql+asyncpg://keprix:changeme@127.0.0.1:5432/keprix"
    )


def _postgres_available() -> bool:
    from keprix.crm.pg_compat import ping_postgres, reset_sync_engine_for_tests

    reset_sync_engine_for_tests()
    return ping_postgres(_pg_url())


@pytest.mark.skipif(not _postgres_available(), reason="Postgres not available for CRM durable tests")
def test_postgres_workspace_isolation_and_crud(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_CRM_BACKEND", "postgres")
    monkeypatch.setenv("KEPRIX_CRM_FORCE_PG", "1")
    monkeypatch.setenv("KEPRIX_DATABASE_URL", _pg_url())
    monkeypatch.setenv("KEPRIX_TEST_DATABASE_URL", _pg_url())

    from keprix.crm.pg_compat import reset_sync_engine_for_tests
    from keprix.config.settings import get_settings

    get_settings.cache_clear()
    reset_sync_engine_for_tests()
    reset_crm_store_for_tests()

    store = CrmStore()
    assert store.backend == "postgres"
    a = store.create_lead("ws_pg_a", name="A", email="a-pg@example.com")
    b = store.create_lead("ws_pg_b", name="B", email="b-pg@example.com")
    assert store.get_lead("ws_pg_b", a["id"]) is None
    assert store.get_lead("ws_pg_a", b["id"]) is None
    assert store.get_lead("ws_pg_a", a["id"])["name"] == "A"
    store.close()


@pytest.mark.skipif(not _postgres_available(), reason="Postgres not available for CRM migrate tests")
def test_migration_dry_run_and_apply_idempotent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_CRM_BACKEND", "sqlite")
    monkeypatch.setenv("KEPRIX_DATABASE_URL", _pg_url())
    monkeypatch.setenv("KEPRIX_TEST_DATABASE_URL", _pg_url())

    from keprix.config.settings import get_settings
    from keprix.crm import migrate_sqlite_to_pg as mig
    from keprix.crm.pg_compat import reset_sync_engine_for_tests
    from keprix.outreach.store import OutreachStore

    get_settings.cache_clear()
    reset_sync_engine_for_tests()

    crm_path = tmp_path / "crm.sqlite"
    outreach_path = tmp_path / "outreach.sqlite"
    crm = CrmStore(path=crm_path)
    crm.create_lead("ws_mig", name="Mig", email="mig@example.com")
    crm.close()
    out = OutreachStore(path=outreach_path)
    out.create_campaign("ws_mig", "Camp")
    out.add_leads("ws_mig", [{"email": "out@example.com", "first_name": "O"}])
    out.close()

    paths = {"crm": crm_path, "outreach": outreach_path}
    dry = mig.dry_run(paths)
    assert dry["mode"] == "dry-run"
    crm_inv = {t["table"]: t["count"] for t in dry["inventory"]["crm"]}
    assert crm_inv.get("crm_leads", 0) >= 1

    first = mig.apply_migration(paths=paths, pg_url=_pg_url(), backup=False)
    second = mig.apply_migration(paths=paths, pg_url=_pg_url(), backup=False)
    assert first["copied"].get("crm_leads", 0) >= 1
    assert second["copied"].get("crm_leads", 0) >= 1
