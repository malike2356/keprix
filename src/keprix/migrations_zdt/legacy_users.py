"""Admin-controlled legacy auth importer with hash verification and idempotency."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

import bcrypt

from keprix.auth.session import _hash_password, auth_manager


def _verify_scrypt(password: str, encoded: str) -> bool:
    parts = encoded.split(":", 1)
    if len(parts) != 2:
        return False
    salt, expected = parts
    try:
        actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1, dklen=len(bytes.fromhex(expected))).hex()
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected.lower())


def _verify(password: str, encoded: str, scheme: str) -> bool:
    if scheme == "bcrypt" or encoded.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            return bcrypt.checkpw(password.encode(), encoded.encode())
        except (ValueError, TypeError):
            return False
    return _verify_scrypt(password, encoded)


def import_legacy_users(source: str, rows: list[dict[str, Any]], *, dry_run: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"source": source, "imported": 0, "skipped_existing": 0, "failed": []}
    existing = {str(user.get("email") or "").strip().lower() for user in auth_manager.list_users() if user.get("email")}
    for index, row in enumerate(rows):
        email = str(row.get("email") or "").strip().lower()
        username = str(row.get("username") or email.split("@", 1)[0]).strip().lower()
        encoded = str(row.get("password_hash") or row.get("hash") or "")
        password = str(row.get("password") or "")
        if not email or not username or not encoded:
            result["failed"].append({"row": index, "error": "email_username_and_password_hash_required"})
            continue
        if email in existing or auth_manager.get_user(username):
            result["skipped_existing"] += 1
            continue
        scheme = "bcrypt" if encoded.startswith(("$2a$", "$2b$", "$2y$")) else "scrypt"
        if not password or not _verify(password, encoded, scheme):
            result["failed"].append({"row": index, "email": email, "error": "password_verification_failed"})
            continue
        if not dry_run:
            auth_manager.create_user(username, password, email=email, is_approved=True)
            existing.add(email)
        result["imported"] += 1
    return result
