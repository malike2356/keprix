"""Session auth manager (ported from Odysseus, adapted for keprix)."""

from __future__ import annotations

import json
import logging
import os
import re
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
SESSION_TOUCH_INTERVAL_SECONDS = 60
RESERVED_USERNAMES = frozenset({"admin", "api", "system", "internal-tool"})
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_RECOVERY_CODE_RE = re.compile(r"[^a-f0-9]")


class ConcurrentSessionLimitError(RuntimeError):
    """Raised when a new login is blocked by the concurrent session policy."""


def _session_policy() -> dict[str, Any]:
    from keprix.sessions import resolve_session_config

    return resolve_session_config()



def _normalize_recovery_code(code: str) -> str:
    return _RECOVERY_CODE_RE.sub("", code.lower())[:8]


def _format_recovery_code(raw: str) -> str:
    cleaned = _normalize_recovery_code(raw)
    if len(cleaned) < 8:
        cleaned = cleaned.ljust(8, "0")
    return f"{cleaned[:4]}-{cleaned[4:8]}".upper()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def _mask_ip(ip: str) -> str | None:
    cleaned = ip.strip()
    if not cleaned:
        return None
    if ":" in cleaned:
        parts = cleaned.split(":")
        if len(parts) >= 2:
            return f"{parts[0]}:{parts[1]}:*"
        return cleaned
    octets = cleaned.split(".")
    if len(octets) == 4:
        return f"{octets[0]}.{octets[1]}.*.*"
    return cleaned


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
                "created_at": time.time(),
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

    def create_session(
        self,
        username: str,
        *,
        device_label: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        location: str | None = None,
    ) -> str:
        from keprix.sessions import (
            NEW_DEVICE_NOTIFIER,
            append_revocation_log,
            enforce_concurrent_limit,
            format_new_login_message,
            parse_device_info,
        )

        policy = _session_policy()
        absolute_s = max(60, int(policy["absolute_max_ms"] / 1000))
        idle_s = max(60, int(policy["idle_timeout_ms"] / 1000))
        device = parse_device_info(
            user_agent=user_agent or device_label,
            ip=ip_address,
            location=location,
            device_label=device_label,
        )
        token = secrets.token_urlsafe(32)
        now = time.time()
        session_id = str(uuid4())
        user_key = username.strip().lower()
        with self._sessions_lock:
            active: list[dict[str, Any]] = []
            for existing_token, meta in list(self._sessions.items()):
                if str(meta.get("username") or "").strip().lower() != user_key:
                    continue
                if float(meta.get("expiry") or 0) <= now:
                    self._sessions.pop(existing_token, None)
                    continue
                active.append(
                    {
                        "session_id": str(meta.get("session_id") or ""),
                        "created_at": float(meta.get("created_at") or now),
                        "token": existing_token,
                        "revoked_at": None,
                    }
                )
            limit = enforce_concurrent_limit(active, policy)
            if not limit.get("allowed"):
                raise ConcurrentSessionLimitError(
                    "Too many active sessions; log out another device first"
                )
            killed_ids = set(limit.get("killed_session_ids") or [])
            if killed_ids:
                for existing_token, meta in list(self._sessions.items()):
                    if str(meta.get("session_id") or "") in killed_ids:
                        self._sessions.pop(existing_token, None)
                        append_revocation_log(
                            user_id=str((self.get_user(user_key) or {}).get("id") or user_key),
                            session_id=str(meta.get("session_id") or ""),
                            reason="concurrent_limit",
                            initiated_by="system",
                        )
            known = False
            for _tok, meta in self._sessions.items():
                if str(meta.get("username") or "").strip().lower() != user_key:
                    continue
                same_label = str(meta.get("device_label") or "").lower() == str(device["device_label"]).lower()
                same_ip = bool(ip_address) and str(meta.get("ip_address") or "") == ip_address
                if same_label or same_ip:
                    known = True
                    break

            self._sessions[token] = {
                "username": user_key,
                "token_hash": hash_token(token),
                "session_id": session_id,
                "expiry": now + absolute_s,
                "idle_expiry": now + idle_s,
                "device_label": device["device_label"],
                "ip_address": ip_address,
                "user_agent": device.get("user_agent"),
                "location": device.get("location"),
                "browser": device.get("browser"),
                "os": device.get("os"),
                "created_at": now,
                "last_seen_at": now,
            }
            self._save_sessions()

        if not known:
            event = {
                "user_id": str((self.get_user(user_key) or {}).get("id") or user_key),
                "session_id": session_id,
                "browser": device.get("browser"),
                "os": device.get("os"),
                "location": device.get("location"),
                "ip": ip_address,
            }
            message = format_new_login_message(
                browser=str(device.get("browser") or "Unknown browser"),
                os_name=str(device.get("os") or "Unknown OS"),
                location=str(device.get("location") or "Unknown location"),
            )
            NEW_DEVICE_NOTIFIER.notify(event, message)
        return token

    def touch_session(self, token: str) -> None:
        now = time.time()
        policy = _session_policy()
        idle_s = max(60, int(policy["idle_timeout_ms"] / 1000))
        with self._sessions_lock:
            meta = self._sessions.get(token)
            if not meta:
                return
            last_seen = float(meta.get("last_seen_at") or 0)
            if now - last_seen < SESSION_TOUCH_INTERVAL_SECONDS:
                return
            meta["last_seen_at"] = now
            meta["idle_expiry"] = now + idle_s
            self._save_sessions()

    def list_sessions(self, user_id: str, *, current_token: str | None = None) -> list[dict[str, Any]]:
        user = self.get_user_by_id(user_id)
        if not user:
            return []
        username = str(user["username"]).strip().lower()
        current_session_id: str | None = None
        if current_token:
            current_meta = self._sessions.get(current_token)
            if current_meta:
                current_session_id = str(current_meta.get("session_id") or "") or None

        rows: list[dict[str, Any]] = []
        migrated = False
        now = time.time()
        with self._sessions_lock:
            for token, meta in list(self._sessions.items()):
                if str(meta.get("username") or "").strip().lower() != username:
                    continue
                if float(meta.get("expiry") or 0) <= now:
                    continue
                session_id = str(meta.get("session_id") or "")
                if not session_id:
                    session_id = str(uuid4())
                    meta["session_id"] = session_id
                    migrated = True
                created_at = float(meta.get("created_at") or meta.get("expiry", now) - TOKEN_TTL_SECONDS)
                last_seen_at = float(meta.get("last_seen_at") or created_at)
                if "created_at" not in meta:
                    meta["created_at"] = created_at
                    migrated = True
                if "last_seen_at" not in meta:
                    meta["last_seen_at"] = last_seen_at
                    migrated = True
                is_current = False
                if current_session_id:
                    is_current = session_id == current_session_id
                elif current_token:
                    is_current = token == current_token
                rows.append(
                    {
                        "session_id": session_id,
                        "device_label": str(meta.get("device_label") or "Unknown device"),
                        "ip_address_masked": _mask_ip(str(meta.get("ip_address") or "")),
                        "created_at": created_at,
                        "last_seen_at": last_seen_at,
                        "is_current": is_current,
                    }
                )
            if migrated:
                self._save_sessions()
        rows.sort(key=lambda row: float(row.get("last_seen_at") or 0), reverse=True)
        return rows

    def revoke_session(self, user_id: str, session_id: str, *, current_token: str | None = None) -> bool:
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        username = str(user["username"]).strip().lower()
        target = session_id.strip()
        if not target:
            return False
        with self._sessions_lock:
            for token, meta in list(self._sessions.items()):
                if str(meta.get("username") or "").strip().lower() != username:
                    continue
                if str(meta.get("session_id") or "") != target:
                    continue
                if current_token and token == current_token:
                    return False
                self._sessions.pop(token, None)
                self._save_sessions()
                return True
        return False

    def revoke_all_sessions(self, user_id: str, *, except_token: str | None = None) -> int:
        user = self.get_user_by_id(user_id)
        if not user:
            return 0
        return self.revoke_other_sessions(str(user["username"]), keep_token=except_token)

    def validate_token(self, token: str) -> dict[str, Any] | None:
        with self._sessions_lock:
            meta = self._sessions.get(token)
            if not meta:
                return None
            now = time.time()
            if meta.get("expiry", 0) <= now:
                self._sessions.pop(token, None)
                self._save_sessions()
                return None
            idle_expiry = float(meta.get("idle_expiry") or meta.get("expiry") or 0)
            if idle_expiry and idle_expiry <= now:
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
            meta = self._sessions.pop(token, None)
            self._save_sessions()
        if meta:
            from keprix.sessions import append_revocation_log

            user = self.get_user(str(meta.get("username") or ""))
            append_revocation_log(
                user_id=str((user or {}).get("id") or meta.get("username") or ""),
                session_id=str(meta.get("session_id") or ""),
                reason="logout",
                initiated_by="user",
            )

    def revoke_other_sessions(self, username: str, *, keep_token: str | None = None) -> int:
        from keprix.sessions import append_revocation_log

        user_key = username.strip().lower()
        user = self.get_user(user_key)
        user_id = str((user or {}).get("id") or user_key)
        removed = 0
        with self._sessions_lock:
            for session_token, meta in list(self._sessions.items()):
                if str(meta.get("username") or "").strip().lower() != user_key:
                    continue
                if keep_token and session_token == keep_token:
                    continue
                self._sessions.pop(session_token, None)
                append_revocation_log(
                    user_id=user_id,
                    session_id=str(meta.get("session_id") or ""),
                    reason="user_request",
                    initiated_by="user",
                )
                removed += 1
            if removed:
                self._save_sessions()
        return removed

    def revoke_all_user_sessions(self, user_id: str, *, reason: str = "password_changed") -> int:
        """Instant revoke of every session for the user (including current)."""
        from keprix.sessions import append_revocation_log

        user = self.get_user_by_id(user_id)
        if not user:
            return 0
        user_key = str(user["username"]).strip().lower()
        removed = 0
        with self._sessions_lock:
            for session_token, meta in list(self._sessions.items()):
                if str(meta.get("username") or "").strip().lower() != user_key:
                    continue
                self._sessions.pop(session_token, None)
                append_revocation_log(
                    user_id=str(user_id),
                    session_id=str(meta.get("session_id") or ""),
                    reason=reason,
                    initiated_by="system",
                )
                removed += 1
            if removed:
                self._save_sessions()
        return removed

    def _set_password_hash(self, user: dict[str, Any], new_password: str) -> None:
        old_hash = str(user.get("password_hash") or "")
        new_hash = _hash_password(new_password)
        if user.get("totp_enabled") and user.get("totp_secret") and old_hash:
            old_key = totp_encryption_key(old_hash.encode("utf-8"))
            secret = decrypt_totp_secret(user["totp_secret"], encryption_key=old_key)
            new_key = totp_encryption_key(new_hash.encode("utf-8"))
            user["totp_secret"] = encrypt_totp_secret(secret, encryption_key=new_key)
        user["password_hash"] = new_hash
        user.pop("totp_secret_pending", None)

    def change_password(self, user_id: str, current: str, new: str) -> tuple[bool, str]:
        if len(new) < 8:
            return False, "Password too short"
        user = self.get_user_by_id(user_id)
        if not user:
            return False, "User not found"
        if not _verify_password(current, user["password_hash"]):
            return False, "Invalid current password"
        with self._config_lock:
            locked_user = self.get_user_by_id(user_id)
            if locked_user is None:
                return False, "User not found"
            if not _verify_password(current, locked_user["password_hash"]):
                return False, "Invalid current password"
            self._set_password_hash(locked_user, new)
            self._save()
        return True, "Password changed"

    def reset_password(self, user_id: str, new: str) -> None:
        if len(new) < 8:
            raise ValueError("Password too short")
        with self._config_lock:
            user = self.get_user_by_id(user_id)
            if user is None:
                raise ValueError("User not found")
            self._set_password_hash(user, new)
            self._save()

    def login(
        self,
        username: str,
        password: str,
        *,
        totp_code: str | None = None,
        recovery_code: str | None = None,
        device_label: str | None = None,
        ip_address: str | None = None,
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
            if password == expected and not _verify_password(password, user["password_hash"]):
                with self._config_lock:
                    locked_user = self.get_user(admin_key)
                    if locked_user is not None:
                        self._set_password_hash(locked_user, expected)
                        self._save()
                        user = locked_user
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

        ok, totp_error = self._verify_login_second_factor(
            user_key,
            totp_code=totp_code,
            recovery_code=recovery_code,
        )
        if not ok:
            return None, None, totp_error

        try:
            token = self.create_session(user_key, device_label=device_label, ip_address=ip_address)
        except ConcurrentSessionLimitError as exc:
            return None, None, str(exc)
        user["last_login_at"] = time.time()
        self._save()
        return token, dict(user), None

    def _verify_login_second_factor(
        self,
        username: str,
        *,
        totp_code: str | None = None,
        recovery_code: str | None = None,
    ) -> tuple[bool, str | None]:
        user = self.get_user(username)
        if not user or not user.get("totp_enabled"):
            return True, None

        if recovery_code:
            if self.consume_recovery_code(username, recovery_code):
                return True, None
            return False, "Invalid recovery code"

        code = (totp_code or "").strip()
        if not code:
            return False, "totp_required"

        if self.totp_verify(username, code):
            return True, None
        return False, "Invalid two-factor code"

    def verify_user_password(self, user_id: str, password: str) -> bool:
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        return _verify_password(password, user["password_hash"])

    def generate_recovery_codes(self, username: str, *, count: int = 10) -> list[str]:
        user = self.get_user(username)
        if not user or not user.get("totp_enabled"):
            raise ValueError("Two-factor is not enabled")

        from keprix.security.sessions import BackupCodeManager

        raw_codes = BackupCodeManager.generate_codes(count)
        display_codes = [_format_recovery_code(code) for code in raw_codes]
        normalized_codes = [_normalize_recovery_code(code) for code in display_codes]
        hashes = BackupCodeManager.hash_codes(normalized_codes)

        with self._config_lock:
            locked = self.get_user(username)
            if locked is None or not locked.get("totp_enabled"):
                raise ValueError("Two-factor is not enabled")
            locked["recovery_code_hashes"] = hashes
            self._save()
        return display_codes

    def consume_recovery_code(self, username: str, code: str) -> bool:
        normalized = _normalize_recovery_code(code)
        if len(normalized) != 8:
            return False
        with self._config_lock:
            user = self.get_user(username)
            if not user:
                return False
            hashes = list(user.get("recovery_code_hashes") or [])
            for idx, stored in enumerate(hashes):
                try:
                    matched = bcrypt.checkpw(normalized.encode("utf-8"), stored.encode("utf-8"))
                except ValueError:
                    matched = False
                if matched:
                    hashes.pop(idx)
                    user["recovery_code_hashes"] = hashes
                    self._save()
                    return True
            return False

    def admin_reset_totp(self, user_id: str) -> bool:
        with self._config_lock:
            user = self.get_user_by_id(user_id)
            if user is None:
                return False
            user["totp_enabled"] = False
            user["totp_secret"] = None
            user.pop("totp_secret_pending", None)
            user.pop("recovery_code_hashes", None)
            self._save()
            return True

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
                "created_at": time.time(),
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

    def totp_disable(
        self,
        username: str,
        *,
        password: str,
        code: str | None = None,
        recovery_code: str | None = None,
        step_up_token: str | None = None,
    ) -> bool:
        user = self.get_user(username)
        if not user or not user.get("totp_enabled"):
            return False
        if not _verify_password(password, user["password_hash"]):
            return False
        if step_up_token:
            from keprix.auth.step_up_store import step_up_store

            if not step_up_store.consume(str(user["id"]), step_up_token):
                return False
        elif recovery_code:
            if not self.consume_recovery_code(username, recovery_code):
                return False
        elif code:
            if not self.totp_verify(username, code):
                return False
        else:
            return False
        user["totp_enabled"] = False
        user["totp_secret"] = None
        user.pop("totp_secret_pending", None)
        user.pop("recovery_code_hashes", None)
        self._save()
        return True

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        for user in self.users.values():
            if user.get("id") == user_id:
                return user
        return None

    def _email_taken(self, email: str, *, exclude_user_id: str | None = None) -> bool:
        target = email.strip().lower()
        if not target:
            return False
        for user in self.users.values():
            if exclude_user_id and user.get("id") == exclude_user_id:
                continue
            if str(user.get("email") or "").strip().lower() == target:
                return True
        return False

    def update_profile(
        self,
        user_id: str,
        *,
        display_name: str | None = None,
        email: str | None = None,
        avatar_url: str | None = None,
        locale: str | None = None,
        timezone: str | None = None,
    ) -> dict[str, Any] | None:
        with self._config_lock:
            user = self.get_user_by_id(user_id)
            if user is None:
                return None

            if email is not None:
                normalized = email.strip().lower()
                if normalized and not _EMAIL_RE.match(normalized):
                    raise ValueError("Invalid email address")
                if normalized and self._email_taken(normalized, exclude_user_id=user_id):
                    raise ValueError("Email already in use")
                user["email"] = normalized or None

            if display_name is not None:
                cleaned = display_name.strip()
                user["display_name"] = cleaned or None

            if avatar_url is not None:
                cleaned = avatar_url.strip()
                user["avatar_url"] = cleaned or None

            if locale is not None:
                cleaned = locale.strip()
                user["locale"] = cleaned or None

            if timezone is not None:
                cleaned = timezone.strip()
                user["timezone"] = cleaned or None

            self._save()
            return dict(user)

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
        role_changed = False
        with self._config_lock:
            for user in self._config.get("users", {}).values():
                if user.get("id") != user_id:
                    continue
                if "role" in fields and fields["role"] != user.get("role"):
                    role_changed = True
                for key in ("role", "is_approved", "is_active", "email"):
                    if key in fields:
                        user[key] = fields[key]
                self._save()
                updated = dict(user)
                break
            else:
                return None
        if role_changed:
            self.revoke_all_user_sessions(user_id, reason="role_changed")
        return updated

    def attach_handoff_metadata(
        self,
        user_id: str,
        *,
        workspace_id: str,
        carina_user_id: str,
        display_name: str | None = None,
    ) -> dict[str, Any] | None:
        with self._config_lock:
            for user in self._config.get("users", {}).values():
                if user.get("id") != user_id:
                    continue
                user["workspace_id"] = workspace_id
                user["carina_user_id"] = carina_user_id
                user["carina_tenant_id"] = workspace_id
                user["auth_source"] = "carina_handoff"
                if display_name and not user.get("display_name"):
                    user["display_name"] = display_name
                self._save()
                return dict(user)
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
