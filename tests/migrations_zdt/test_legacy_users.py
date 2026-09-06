from __future__ import annotations

import hashlib

from keprix.migrations_zdt.legacy_users import import_legacy_users


def test_bcrypt_import_is_idempotent(monkeypatch):
    from keprix.migrations_zdt import legacy_users

    class FakeAuth:
        def __init__(self):
            self.rows = []

        def list_users(self):
            return self.rows

        def get_user(self, username):
            return next((row for row in self.rows if row["username"] == username), None)

        def create_user(self, username, password, **kwargs):
            self.rows.append({"username": username, **kwargs})

    auth = FakeAuth()
    monkeypatch.setattr(legacy_users, "auth_manager", auth)
    import bcrypt

    encoded = bcrypt.hashpw(b"secret", bcrypt.gensalt()).decode()
    row = {"email": "a@example.com", "password_hash": encoded, "password": "secret"}
    assert import_legacy_users("scout", [row])["imported"] == 1
    assert import_legacy_users("scout", [row])["skipped_existing"] == 1


def test_hash_only_scrypt_row_fails_without_plaintext():
    result = import_legacy_users("carina", [{"email": "a@example.com", "password_hash": "salt:00"}])
    assert result["imported"] == 0
    assert result["failed"][0]["error"] == "password_verification_failed"
