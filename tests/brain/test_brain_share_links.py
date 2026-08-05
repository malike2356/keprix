from pathlib import Path

import pytest

from keprix.brain.share_links import share_link_store


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))


def test_share_link_password_and_expiry() -> None:
    link = share_link_store.create(
        workspace_id="ws-share",
        created_by="user-1",
        scope="memories_only",
        expires_in_days=1,
        password="hunter2",
    )
    fetched = share_link_store.get(link.share_id)
    assert fetched is not None
    assert share_link_store.verify_password(fetched, "hunter2")
    assert not share_link_store.verify_password(fetched, "wrong")
    assert not share_link_store.is_expired(fetched)

    share_link_store.record_access(link.share_id)
    updated = share_link_store.get(link.share_id)
    assert updated is not None
    assert updated.access_count == 1

    assert share_link_store.revoke(link.share_id, "ws-share")
    assert share_link_store.get(link.share_id) is None
