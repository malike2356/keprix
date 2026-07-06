"""Browser profile encryption tests."""

import json

from keprix.browser.browser_profile import ProfileKind, get_profile_store
from keprix.security.vault_service import _decrypt_bytes


def test_profiles_are_workspace_scoped() -> None:
    store = get_profile_store()
    profile = store.create(workspace_id="ws-a", name="work", kind=ProfileKind.PERSISTENT)
    assert store.get(profile.id, "ws-a") is not None
    assert store.get(profile.id, "ws-b") is None


def test_profile_state_encrypted_at_rest() -> None:
    store = get_profile_store()
    profile = store.create(workspace_id="ws-a", name="auth", kind=ProfileKind.AUTHENTICATED)
    store.save_state(profile.id, "ws-a", {"cookies": [{"name": "sid", "value": "secret"}], "sessions": []})
    blob_path = store._state_path(profile.id)
    raw = blob_path.read_bytes()
    assert b"secret" not in raw
    loaded = store.load_state(profile.id, "ws-a")
    assert loaded["cookies"][0]["value"] == "secret"
    plaintext = _decrypt_bytes(raw)
    assert json.loads(plaintext.decode("utf-8"))["cookies"][0]["value"] == "secret"


def test_read_only_profile_rejects_state_writes() -> None:
    store = get_profile_store()
    profile = store.create(workspace_id="ws-a", name="ro", kind=ProfileKind.READ_ONLY)
    try:
        store.save_state(profile.id, "ws-a", {"cookies": [], "sessions": []})
        raised = False
    except PermissionError:
        raised = True
    assert raised
