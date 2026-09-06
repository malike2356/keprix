from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[2]
MIGRATION = ROOT / "migrations" / "versions" / "040_postgres_tenant_rls.py"
INVENTORY = ROOT / "docs" / "security" / "postgres-tenant-rls-inventory.md"


def test_rls_migration_forces_policies_and_fails_closed() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "FORCE ROW LEVEL SECURITY" in sql
    assert "current_setting(''app.current_tenant_id'', true)" in sql
    assert "WITH CHECK" in sql
    assert "control_plane_memberships" in sql
    assert "control_plane_workspaces" in sql
    assert "cpw.workspace_id = %I.%I" in sql
    assert "cpm.user_id = %I.%I" in sql


def test_rls_inventory_declares_global_exceptions_and_runtime_audit() -> None:
    text = INVENTORY.read_text(encoding="utf-8")
    assert "control_plane_tenants" in text
    assert "user_id` with `tenant_id" in text
    assert "information_schema.columns" in text
    assert "Prompt 014" in text
