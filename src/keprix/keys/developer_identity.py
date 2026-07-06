"""
Developer identity bootstrap for Keprix.

Called during ``keprix init`` when the user confirms they are the installation owner.
Generates a local RSA keypair and a self-signed developer identity record.
No remote server is involved.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import platform
import secrets
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey

from keprix.config.constants import (
    AUDIT_DEVELOPER_IDENTITY_CREATED,
    AUDIT_DEVELOPER_IDENTITY_REVOKED,
    DEVELOPER_CONFIG_DIR,
    DEVELOPER_IDENTITY_DIR,
    PRODUCT_NAME,
    PRODUCT_VERSION,
)

logger = logging.getLogger(__name__)

IDENTITY_VERSION = 1
PRIVATE_KEY_NAME = "developer.key"
PUBLIC_KEY_NAME = "developer.pub"
DEV_JSON_NAME = "dev.json"
AUDIT_LOG_NAME = "audit.log"
CONFIG_ENV_NAME = "config.env"

_FILE_MODE = 0o600
_DIR_MODE = 0o700


def _expand(path: str) -> Path:
    return Path(path).expanduser()


def get_identity_dir() -> Path:
    return _expand(DEVELOPER_IDENTITY_DIR)


def get_config_dir() -> Path:
    return _expand(DEVELOPER_CONFIG_DIR)


def _secure_write(path: Path, content: str | bytes, *, binary: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent != path:
        try:
            path.parent.chmod(_DIR_MODE)
        except OSError:
            pass
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    mode = stat.S_IRUSR | stat.S_IWUSR
    data = content if binary else content.encode("utf-8")
    fd = os.open(str(path), flags, mode)
    try:
        os.write(fd, data)
        os.fchmod(fd, _FILE_MODE)
    finally:
        os.close(fd)


def _machine_id() -> str:
    candidates = [
        Path("/etc/machine-id"),
        Path("/var/lib/dbus/machine-id"),
    ]
    for candidate in candidates:
        try:
            if candidate.is_file():
                value = candidate.read_text(encoding="utf-8").strip()
                if value:
                    return value
        except OSError:
            continue
    return platform.node() or "unknown-host"


def installation_fingerprint() -> str:
    """Stable fingerprint for this machine (no network call)."""
    parts = [
        platform.system(),
        platform.machine(),
        platform.node(),
        _machine_id(),
    ]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest


def _hostname_hash() -> str:
    return hashlib.sha256(platform.node().encode("utf-8")).hexdigest()


def _load_private_key(path: Path) -> RSAPrivateKey:
    data = path.read_bytes()
    key = serialization.load_pem_private_key(data, password=None)
    if not isinstance(key, RSAPrivateKey):
        raise TypeError("Expected RSA private key")
    return key


def _load_public_key(path: Path) -> RSAPublicKey:
    data = path.read_bytes()
    key = serialization.load_pem_public_key(data)
    if not isinstance(key, RSAPublicKey):
        raise TypeError("Expected RSA public key")
    return key


def _public_key_pem(public_key: RSAPublicKey) -> str:
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def _sign_payload(private_key: RSAPrivateKey, payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = private_key.sign(
        canonical,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("ascii")


def _verify_signature(public_key: RSAPublicKey, payload: dict[str, Any], signature_b64: str) -> bool:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    try:
        signature = base64.b64decode(signature_b64.encode("ascii"))
        public_key.verify(signature, canonical, padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception:
        return False


def _append_audit(event_type: str, detail: dict[str, Any]) -> None:
    audit_path = get_identity_dir() / AUDIT_LOG_NAME
    entry = {
        "event_type": event_type,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "product": PRODUCT_NAME,
        "detail": detail,
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    try:
        audit_path.chmod(_FILE_MODE)
    except OSError:
        pass


def _write_config_env(*, developer_mode: bool, ip_hash_salt: str | None = None) -> None:
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    try:
        config_dir.chmod(_DIR_MODE)
    except OSError:
        pass
    config_path = config_dir / CONFIG_ENV_NAME
    lines: list[str] = []
    if config_path.is_file():
        lines = config_path.read_text(encoding="utf-8").splitlines()
    env_map: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        env_map[key.strip()] = value.strip()
    env_map["KEPRIX_DEVELOPER_MODE"] = "true" if developer_mode else "false"
    if ip_hash_salt and "KEPRIX_IP_HASH_SALT" not in env_map:
        env_map["KEPRIX_IP_HASH_SALT"] = ip_hash_salt
    rendered = "\n".join(f"{key}={value}" for key, value in sorted(env_map.items())) + "\n"
    _secure_write(config_path, rendered)


def create_developer_identity(*, force: bool = False) -> dict[str, Any]:
    """
    Generate RSA-2048 keypair and signed developer identity record.

    Writes to ``~/.keprix/identity/`` with mode 0600 and sets developer mode in config.env.
    """
    identity_dir = get_identity_dir()
    dev_json_path = identity_dir / DEV_JSON_NAME
    if dev_json_path.exists() and not force:
        raise FileExistsError(
            "Developer identity already exists. Use 'keprix identity revoke' first, or pass force=True."
        )

    identity_dir.mkdir(parents=True, exist_ok=True)
    try:
        identity_dir.chmod(_DIR_MODE)
    except OSError:
        pass

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    _secure_write(identity_dir / PRIVATE_KEY_NAME, private_pem, binary=True)
    _secure_write(identity_dir / PUBLIC_KEY_NAME, public_pem, binary=True)

    payload: dict[str, Any] = {
        "product": PRODUCT_NAME.lower(),
        "version": PRODUCT_VERSION,
        "identity_version": IDENTITY_VERSION,
        "installation_fingerprint": installation_fingerprint(),
        "hostname_hash": _hostname_hash(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "public_key_pem": _public_key_pem(public_key),
    }
    signature = _sign_payload(private_key, payload)
    record = {"payload": payload, "signature": signature}
    _secure_write(dev_json_path, json.dumps(record, indent=2))

    ip_hash_salt = secrets.token_hex(32)
    _write_config_env(developer_mode=True, ip_hash_salt=ip_hash_salt)
    _append_audit(
        AUDIT_DEVELOPER_IDENTITY_CREATED,
        {"installation_fingerprint": payload["installation_fingerprint"]},
    )
    logger.info("Developer identity created at %s", identity_dir)
    return get_identity_status()


def verify_developer_identity() -> bool:
    """Validate local developer identity without any network call."""
    identity_dir = get_identity_dir()
    dev_json_path = identity_dir / DEV_JSON_NAME
    public_key_path = identity_dir / PUBLIC_KEY_NAME
    if not dev_json_path.is_file() or not public_key_path.is_file():
        return False
    try:
        record = json.loads(dev_json_path.read_text(encoding="utf-8"))
        payload = record.get("payload") or {}
        signature = record.get("signature") or ""
        if payload.get("installation_fingerprint") != installation_fingerprint():
            return False
        public_key = _load_public_key(public_key_path)
        if not _verify_signature(public_key, payload, signature):
            return False
        stored_pem = (payload.get("public_key_pem") or "").strip()
        if stored_pem and stored_pem != _public_key_pem(public_key).strip():
            return False
        return True
    except Exception:
        logger.debug("Developer identity verification failed", exc_info=True)
        return False


def get_identity_status() -> dict[str, Any]:
    """Return a summary of the current developer identity state."""
    identity_dir = get_identity_dir()
    dev_json_path = identity_dir / DEV_JSON_NAME
    valid = verify_developer_identity()
    created_at: str | None = None
    fingerprint: str | None = None
    if dev_json_path.is_file():
        try:
            record = json.loads(dev_json_path.read_text(encoding="utf-8"))
            payload = record.get("payload") or {}
            created_at = payload.get("created_at")
            fingerprint = payload.get("installation_fingerprint")
        except Exception:
            pass
    return {
        "product": PRODUCT_NAME,
        "valid": valid,
        "developer_mode": valid,
        "identity_dir": str(identity_dir),
        "created_at": created_at,
        "installation_fingerprint": fingerprint,
        "current_fingerprint": installation_fingerprint(),
    }


def revoke_developer_identity() -> None:
    """Remove developer identity files and disable developer mode."""
    identity_dir = get_identity_dir()
    for name in (PRIVATE_KEY_NAME, PUBLIC_KEY_NAME, DEV_JSON_NAME):
        path = identity_dir / name
        if path.is_file():
            path.unlink()
    _write_config_env(developer_mode=False)
    _append_audit(AUDIT_DEVELOPER_IDENTITY_REVOKED, {})
    logger.info("Developer identity revoked")
