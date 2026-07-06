"""Session auth manager (ported from Odysseus, adapted for keprix)."""

from __future__ import annotations

import json
import logging
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import bcrypt

from keprix.auth.config import admin_email, admin_password, admin_username, data_dir, multi_user_enabled, require_approval
from keprix.auth.totp import (
    decrypt_totp_secret,
    encrypt_totp_secret,
    generate_totp_secret,
    totp_encryption_key,
    verify_totp_code,
)
from keprix.security.crypto import hash_token

logger = logging.getLogger(__name__)

TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7
RESERVED_USERNAMES = frozenset({"admin", "api", "system", "internal-tool"})


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


class AuthManager:
    """File-backed auth with optional multi-user registration."""

    def __init__(self, auth_path: str | None = None) -> None:
        base = Path(data_dir())
        base.mkdir(parents=True, exist_ok=True)
        self.auth_path = auth_path or str(base / "auth.json")
        self.sessions_path = str(Path(self.auth_path).with_name("sessions.json"))
        self._config: dict[str, Any] = {}
        self._sessions: dict[str, dict[str, Any]] = {}
        self._config_lock = threading.Lock()
        self._sessions_lock = threading.RLock()
        self._load()
        self._load_sessions()
        self._bootstrap_admin_from_env()

    def _load(self) -> None:
        path = Path(self.auth_path)
        if path.exists():
            try:
                self._config = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.error("Failed to load auth config: %s", exc)
                self._config = {}
        else:
            self._config = {}

    def _save(self) -> None:
        path = Path(self.auth_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._config, indent=2), encoding="utf-8")
        os.chmod(path, 0o600)

    def _load_sessions(self) -> None:
        path = Path(self.sessions_path)
        if not path.exists():
            self._sessions = {}
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            now = time.time()
            self._sessions = {token: meta for token, meta in data.items() if meta.get("expiry", 0) > now}
        except Exception:
            self._sessions = {}

    def _save_sessions(self) -> None:
        path = Path(self.sessions_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._sessions, indent=2), encoding="utf-8")
        os.chmod(path, 0o600)

    def _bootstrap_admin_from_env(self) -> None:
        password = admin_password()
        if not password:
            return
        user_key = admin_username()
        email = admin_email() or None
        users = self._config.setdefault("users", {})
        existing = users.get(user_key)
        if existing is None:
            users[user_key] = {
                "id": str(uuid4()),
                "username": user_key,
                "email": email,
                "password_hash": _hash_password(password),
                "role": "admin",
                "totp_enabled": False,
                "totp_secret": None,
                "is_approved": True,
                "is_active": True,
            }
            self._save()
            return
        changed = False
        if email and existing.get("email") != email:
            existing["email"] = email
            changed = True
        if existing.get("role") != "admin":
            existing["role"] = "admin"
            changed = True
        stored_hash = str(existing.get("password_hash") or "")
        if stored_hash and not _verify_password(password, stored_hash):
            existing["password_hash"] = _hash_password(password)
            changed = True
        elif not stored_hash:
            existing["password_hash"] = _hash_password(password)
            changed = True
        if changed:
            self._save()

    def guest_user(self) -> dict[str, Any]:
        user = self.get_user(admin_username())
        if user:
            return dict(user)
        return {
            "id": admin_username(),
            "username": admin_username(),
            "email": admin_email() or None,
            "role": "admin",
            "totp_enabled": False,
            "is_approved": True,
            "is_active": True,
        }

    @property
    def users(self) -> dict[str, Any]:
        return dict(self._config.get("users", {}))

    def get_user(self, username: str) -> dict[str, Any] | None:
        return self.users.get(username.strip().lower())

    def _find_user_by_login(self, login: str) -> dict[str, Any] | None:
        user_key = login.strip().lower()
        user = self.get_user(user_key)
        if user:
            return user
        for candidate in self.users.values():
            email = str(candidate.get("email") or "").strip().lower()
            if email and email == user_key:
                return candidate
        return None

    def create_session(self, username: str, *, device_label: str | None = None) -> str:
        token = secrets.token_urlsafe(32)
        with self._sessions_lock:
            self._sessions[token] = {
                "username": username,
                "token_hash": hash_token(token),
                "expiry": time.time() + TOKEN_TTL_SECONDS,
                "device_label": device_label,
            }
            self._save_sessions()
        return token

    def validate_token(self, token: str) -> dict[str, Any] | None:
        with self._sessions_lock:
            meta = self._sessions.get(token)
            if not meta:
                return None
            if meta.get("expiry", 0) <= time.time():
                self._sessions.pop(token, None)
                self._save_sessions()
                return None
            user = self.get_user(meta["username"])
            if not user or not user.get("is_active", True):
                return None
            if multi_user_enabled() and require_approval() and not user.get("is_approved", False):
                return None
            return user

    def revoke_token(self, token: str) -> None:
        with self._sessions_lock:
            self._sessions.pop(token, None)
            self._save_sessions()

    def login(
        self,
        username: str,
        password: str,
        *,
        totp_code: str | None = None,
    ) -> tuple[str | None, dict[str, Any] | None, str | None]:
        user_key = username.strip().lower()
        user = self._find_user_by_login(username)
        if user:
            user_key = str(user.get("username") or user_key).strip().lower()

        if not multi_user_enabled():
            expected = admin_password()
            admin_key = admin_username()
            if not expected or user_key != admin_key:
                return None, None, "Invalid credentials"
            self._bootstrap_admin_from_env()
            user = self.get_user(admin_key)
            if user is None:
                return None, None, "Invalid credentials"
            if not (_verify_password(password, user["password_hash"]) or password == expected):
                return None, None, "Invalid credentials"
        else:
            if not user:
                return None, None, "Invalid credentials"
            if not _verify_password(password, user["password_hash"]):
                return None, None, "Invalid credentials"
            if require_approval() and not user.get("is_approved", False):
                return None, None, "Account pending approval"
            if not user.get("is_active", True):
                return None, None, "Account deactivated"

        if not self.totp_verify(user_key, totp_code or ""):
            return None, None, "Invalid two-factor code"

        token = self.create_session(user_key)
        user["last_login_at"] = time.time()
        self._save()
        return token, dict(user), None

    def register(self, username: str, password: str, *, email: str | None = None) -> tuple[bool, str]:
        if not multi_user_enabled():
            return False, "Registration disabled"
        user_key = username.strip().lower()
        if not user_key or user_key in RESERVED_USERNAMES:
            return False, "Invalid username"
        if len(password) < 8:
            return False, "Password too short"
        with self._config_lock:
            users = self._config.setdefault("users", {})
            if user_key in users:
                return False, "Username already exists"
            users[user_key] = {
                "id": str(uuid4()),
                "username": user_key,
                "email": email,
                "password_hash": _hash_password(password),
                "role": "user",
                "totp_enabled": False,
                "totp_secret": None,
                "is_approved": not require_approval(),
                "is_active": True,
            }
            self._save()
        return True, "Registered"

    def totp_verify(self, username: str, code: str) -> bool:
        user = self.get_user(username)
        if not user:
            return False
        if not user.get("totp_enabled"):
            return True
        encrypted = user.get("totp_secret")
        if not encrypted:
            return False
        key = totp_encryption_key(user["password_hash"].encode("utf-8"))
        secret = decrypt_totp_secret(encrypted, encryption_key=key)
        return verify_totp_code(secret, code)

    def totp_setup(self, username: str) -> tuple[str, str]:
        user = self.get_user(username)
        if not user:
            raise ValueError("User not found")
        secret = generate_totp_secret()
        key = totp_encryption_key(user["password_hash"].encode("utf-8"))
        user["totp_secret_pending"] = encrypt_totp_secret(secret, encryption_key=key)
        self._save()
        from keprix.auth.totp import totp_provisioning_uri

        return secret, totp_provisioning_uri(secret, username=username)

    def totp_confirm(self, username: str, code: str) -> bool:
        user = self.get_user(username)
        if not user or not user.get("totp_secret_pending"):
            return False
        key = totp_encryption_key(user["password_hash"].encode("utf-8"))
        secret = decrypt_totp_secret(user["totp_secret_pending"], encryption_key=key)
        if not verify_totp_code(secret, code):
            return False
        user["totp_secret"] = user.pop("totp_secret_pending")
        user["totp_enabled"] = True
        self._save()
        return True

    def totp_disable(self, username: str, code: str) -> bool:
        user = self.get_user(username)
        if not user or not user.get("totp_enabled"):
            return False
        if not self.totp_verify(username, code):
            return False
        user["totp_enabled"] = False
        user["totp_secret"] = None
        user.pop("totp_secret_pending", None)
        self._save()
        return True

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        for user in self.users.values():
            if user.get("id") == user_id:
                return user
        return None

    def set_password_and_approve(
        self,
        user_id: str,
        password: str,
        *,
        role: str | None = None,
    ) -> dict[str, Any] | None:
        if len(password) < 8:
            raise ValueError("Password too short")
        with self._config_lock:
            for user in self._config.get("users", {}).values():
                if user.get("id") != user_id:
                    continue
                user["password_hash"] = _hash_password(password)
                user["is_approved"] = True
                user["is_active"] = True
                if role is not None:
                    user["role"] = role
                self._save()
                return user
        return None

    def list_users(self) -> list[dict[str, Any]]:
        return [
            {
                "id": user["id"],
                "username": user["username"],
                "email": user.get("email"),
                "role": user.get("role", "user"),
                "is_approved": user.get("is_approved", False),
                "is_active": user.get("is_active", True),
                "totp_enabled": user.get("totp_enabled", False),
                "last_login_at": user.get("last_login_at"),
                "created_at": user.get("created_at"),
            }
            for user in self.users.values()
        ]

    def update_user(self, user_id: str, **fields: Any) -> dict[str, Any] | None:
        with self._config_lock:
            for user in self._config.get("users", {}).values():
                if user.get("id") != user_id:
                    continue
                for key in ("role", "is_approved", "is_active", "email"):
                    if key in fields:
                        user[key] = fields[key]
                self._save()
                return user
        return None

    def delete_user(self, user_id: str) -> bool:
        with self._config_lock:
            users = self._config.get("users", {})
            target = None
            for username, user in users.items():
                if user.get("id") == user_id:
                    target = username
                    break
            if not target:
                return False
            users.pop(target)
            self._save()
            return True

    def create_user(
        self,
        username: str,
        password: str,
        *,
        role: str = "user",
        email: str | None = None,
        is_approved: bool = True,
    ) -> dict[str, Any]:
        user_key = username.strip().lower()
        with self._config_lock:
            users = self._config.setdefault("users", {})
            if user_key in users:
                raise ValueError("Username already exists")
            user = {
                "id": str(uuid4()),
                "username": user_key,
                "email": email,
                "password_hash": _hash_password(password),
                "role": role,
                "totp_enabled": False,
                "totp_secret": None,
                "is_approved": is_approved,
                "is_active": True,
                "created_at": time.time(),
            }
            users[user_key] = user
            self._save()
            return user


auth_manager = AuthManager()
