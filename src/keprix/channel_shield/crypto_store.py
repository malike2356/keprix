"""Encrypted immutable raw payload storage for Channel Shield."""

from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path

from keprix.email.crypto import decrypt_secret, encrypt_secret


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encrypt_bytes(data: bytes) -> str:
    """Encrypt bytes to a text token (Fernet or base64 fallback)."""
    b64 = base64.b64encode(data).decode("ascii")
    return encrypt_secret(b64)


def decrypt_bytes(token: str) -> bytes:
    plain = decrypt_secret(token)
    try:
        return base64.b64decode(plain.encode("ascii"))
    except Exception:
        return plain.encode("utf-8")


def write_raw_blob(store_dir: str, blob_id: str, data: bytes) -> str:
    """Persist encrypted blob under store_dir; return storage URI."""
    root = Path(store_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{blob_id}.enc"
    path.write_text(encrypt_bytes(data), encoding="utf-8")
    return f"shield://raw/{blob_id}"


def read_raw_blob(store_dir: str, blob_id: str) -> bytes | None:
    path = Path(store_dir) / f"{blob_id}.enc"
    if not path.is_file():
        return None
    return decrypt_bytes(path.read_text(encoding="utf-8"))


def destroy_raw_blob(store_dir: str, blob_id: str) -> bool:
    path = Path(store_dir) / f"{blob_id}.enc"
    if not path.is_file():
        return False
    try:
        # Overwrite then unlink
        size = path.stat().st_size
        path.write_bytes(os.urandom(min(size, 4096)))
        path.unlink(missing_ok=True)
        return True
    except OSError:
        return False
