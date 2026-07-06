"""Session management tests."""

import pytest

from keprix.config.settings import get_settings
from keprix.security.sessions import BackupCodeManager, SessionStore, TotpManager


@pytest.fixture(autouse=True)
def in_memory_sessions(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KEPRIX_REDIS_URL", "")
    get_settings.cache_clear()
    import keprix.security.sessions as sessions_mod

    sessions_mod._store = None
    yield
    sessions_mod._store = None
    get_settings.cache_clear()


def test_session_create_and_get():
    store = SessionStore()
    token, record = store.create_session("user-1", ip="127.0.0.1", user_agent="pytest")
    loaded = store.get_session(token)
    assert loaded is not None
    assert loaded.user_id == "user-1"
    assert loaded.session_id == record.session_id


def test_logout_deletes_session():
    store = SessionStore()
    token, _ = store.create_session("user-1")
    store.delete_session(token)
    assert store.get_session(token) is None


def test_session_listing():
    store = SessionStore()
    store.create_session("user-1")
    store.create_session("user-1")
    store.create_session("user-2")
    sessions = store.list_sessions("user-1")
    assert len(sessions) == 2


def test_totp_roundtrip():
    manager = TotpManager(issuer="Keprix")
    secret = manager.generate_secret()
    code = TotpManager(issuer="Keprix").verify(secret, "000000")
    assert code is False
    import pyotp

    valid_code = pyotp.TOTP(secret).now()
    assert manager.verify(secret, valid_code) is True


def test_backup_codes_hash_and_verify():
    codes = BackupCodeManager.generate_codes(3)
    hashed = BackupCodeManager.hash_codes(codes)
    assert BackupCodeManager.verify_code(codes[0], hashed) is True
    assert BackupCodeManager.verify_code("bad-code", hashed) is False
