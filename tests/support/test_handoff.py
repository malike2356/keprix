"""Support handoff privacy tests."""

from __future__ import annotations

import pytest

from keprix.support.handoff import create_handoff
from keprix.support.store import SupportStore


@pytest.fixture()
def support_store(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    import keprix.support.store as store_module

    store = SupportStore(base_dir=tmp_path / "support")
    store_module._store = store
    return store


@pytest.mark.asyncio
async def test_human_handoff_respects_privacy_settings(support_store) -> None:
    support_store.save_privacy_settings(
        {"allow_contact_email": False, "allow_diagnostics_in_handoff": False}
    )
    minimal = await create_handoff(
        category="bug",
        summary="Crash on startup",
        privacy="minimal",
        contact_email="user@example.com",
    )
    assert minimal["contact_email"] is None
    assert minimal["diagnostics"] is None

    standard = await create_handoff(
        category="bug",
        summary="Crash on startup",
        privacy="standard",
        contact_email="user@example.com",
    )
    assert standard["contact_email"] is None
    assert standard["diagnostics"] is None
