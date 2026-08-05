"""Playbook version store tests."""

from __future__ import annotations

from pathlib import Path

from keprix.playbook.version_store import PlaybookVersionStore, canonical_playbook_hash


def test_hash_stability_across_key_order() -> None:
    first = {"id": "demo", "name": "Demo", "steps": [{"id": "a"}], "edges": []}
    second = {"edges": [], "steps": [{"id": "a"}], "name": "Demo", "id": "demo"}

    assert canonical_playbook_hash(first) == canonical_playbook_hash(second)


def test_record_and_list_versions(tmp_path: Path) -> None:
    store = PlaybookVersionStore(tmp_path)
    version = store.record_publish(
        playbook_id="demo",
        version_hash="abc",
        publisher_user_id="user-1",
        scope="personal",
        status="published",
    )

    assert version.version_hash == "abc"
    current = store.get_current("demo", scope="personal")
    assert current is not None
    assert current.version_hash == "abc"
    assert [item.version_hash for item in store.list_versions("demo")] == ["abc"]
