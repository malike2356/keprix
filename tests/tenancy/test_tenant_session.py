from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).parents[2]
SESSION = ROOT / "src" / "keprix" / "db" / "tenant_session.py"


def test_tenant_session_uses_transaction_local_set_config() -> None:
    source = SESSION.read_text(encoding="utf-8")
    assert "class TenantAsyncSession" in source
    assert "set_config('app.current_tenant_id', :tenant_id, true)" in source
    assert "_tenant_setting_set = False" in source
    assert "async def commit" in source
    assert "async def rollback" in source


def test_tenant_setting_is_parameterized() -> None:
    assert ":tenant_id" in text(
        "SELECT set_config('app.current_tenant_id', :tenant_id, true)"
    ).text
