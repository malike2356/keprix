"""
Developer identity bootstrap for keprix.

Called once during `keprix init` when the user confirms they are the
installation owner. Generates a local keypair and a self-signed developer
identity token. No remote server is involved.

The token grants full access on this machine only. It is not transferable.
Add additional local users via keprix's user management (Prompt 08), not
via any commercial key server.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import socket
import time
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from keprix.config.constants import (
    AUDIT_DEVELOPER_IDENTITY_CREATED,
    DEVELOPER_IDENTITY_DIR,
    PRODUCT_VERSION,
)

logger = logging.getLogger(__name__)

_IDENTITY_DIR = Path(DEVELOPER_IDENTITY_DIR).expanduser()
_PRIVATE_KEY_PATH = _IDENTITY_DIR / "private.pem"
_PUBLIC_KEY_PATH = _IDENTITY_DIR / "public.pem"
_DEV_TOKEN_PATH = _IDENTITY_DIR / "dev.json"
_CONFIG_ENV_PATH = Path("~/.keprix/config.env").expanduser()


def _machine_fingerprint() -> str:
    """Return a stable SHA-256 hash of hostname + machine identifier."""
    parts = [
        socket.gethostname(),
        platform.node(),
        platform.machine(),
        str(os.getuid()) if hasattr(os, "getuid") else "",
    ]
    raw = "|".join(parts).encode()
    return hashlib.sha256(raw).hexdigest()


def _generate_keypair() -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    return private_key, private_key.public_key()


def _sign(private_key: rsa.RSAPrivateKey, data: bytes) -> bytes:
    return private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())


def _load_private_key() -> rsa.RSAPrivateKey:
    with open(_PRIVATE_KEY_PATH, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def _load_public_key() -> rsa.RSAPublicKey:
    with open(_PUBLIC_KEY_PATH, "rb") as f:
        return serialization.load_pem_public_key(f.read())


def create_developer_identity() -> Path:
    """
    Generate a developer identity for this installation.

    Creates:
      ~/.keprix/identity/private.pem
      ~/.keprix/identity/public.pem
      ~/.keprix/identity/dev.json
      ~/.keprix/config.env

    Returns the path to dev.json.
    """
    _IDENTITY_DIR.mkdir(parents=True, mode=0o700, exist_ok=True)

    private_key, public_key = _generate_keypair()

    _PRIVATE_KEY_PATH.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    _PRIVATE_KEY_PATH.chmod(0o600)

    _PUBLIC_KEY_PATH.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    fingerprint = _machine_fingerprint()
    hostname_hash = hashlib.sha256(socket.gethostname().encode()).hexdigest()

    record: dict = {
        "product": "keprix",
        "version": PRODUCT_VERSION,
        "fingerprint": fingerprint,
        "hostname_hash": hostname_hash,
        "created_at": int(time.time()),
        "platform": platform.system(),
    }

    payload = json.dumps(record, sort_keys=True).encode()
    signature = _sign(private_key, payload)

    token = {
        "record": record,
        "signature": signature.hex(),
        "public_key": public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode(),
    }

    _DEV_TOKEN_PATH.write_text(json.dumps(token, indent=2))
    _DEV_TOKEN_PATH.chmod(0o600)

    _write_config_env()

    _audit_log(AUDIT_DEVELOPER_IDENTITY_CREATED, fingerprint)

    logger.info("Developer identity created at %s", _DEV_TOKEN_PATH)
    return _DEV_TOKEN_PATH


def _write_config_env() -> None:
    _CONFIG_ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if _CONFIG_ENV_PATH.exists():
        for line in _CONFIG_ENV_PATH.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()
    existing["KEPRIX_DEVELOPER_MODE"] = "true"
    lines = [f"{k}={v}" for k, v in existing.items()]
    _CONFIG_ENV_PATH.write_text("\n".join(lines) + "\n")
    _CONFIG_ENV_PATH.chmod(0o600)


def _audit_log(event_type: str, fingerprint: str) -> None:
    audit_dir = Path("~/.keprix/audit").expanduser()
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / "identity.jsonl"
    entry = {
        "event": event_type,
        "fingerprint": fingerprint,
        "ts": int(time.time()),
    }
    with open(audit_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def verify_developer_identity() -> bool:
    """
    Verify the developer identity token for this machine.

    Returns True if:
    - dev.json exists
    - The signature is valid against the embedded public key
    - The fingerprint matches this machine

    No network call is made.
    """
    if not _DEV_TOKEN_PATH.exists():
        return False
    try:
        token = json.loads(_DEV_TOKEN_PATH.read_text())
        record: dict = token["record"]
        signature = bytes.fromhex(token["signature"])
        public_key_pem: str = token["public_key"]

        public_key: rsa.RSAPublicKey = serialization.load_pem_public_key(
            public_key_pem.encode()
        )
        payload = json.dumps(record, sort_keys=True).encode()
        public_key.verify(signature, payload, padding.PKCS1v15(), hashes.SHA256())

        if record.get("fingerprint") != _machine_fingerprint():
            logger.warning("Developer identity fingerprint mismatch - token is not for this machine")
            return False

        return True
    except Exception as exc:
        logger.warning("Developer identity verification failed: %s", exc)
        return False


def revoke_developer_identity() -> None:
    """Remove the developer identity from this machine."""
    fingerprint = _machine_fingerprint()
    for path in [_DEV_TOKEN_PATH, _PRIVATE_KEY_PATH, _PUBLIC_KEY_PATH]:
        if path.exists():
            path.unlink()
    _audit_log(AUDIT_DEVELOPER_IDENTITY_CREATED.replace("created", "revoked"), fingerprint)
    logger.info("Developer identity revoked")
