"""TOTP helpers with encrypted secret storage."""

from __future__ import annotations

import base64
import os

import pyotp

from keprix.security.crypto import decrypt_text, encrypt_text, derive_key


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def totp_provisioning_uri(secret: str, *, username: str, issuer: str = "keprix") -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=issuer)


def verify_totp_code(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def encrypt_totp_secret(secret: str, *, encryption_key: bytes) -> str:
    return encrypt_text(secret, encryption_key)


def decrypt_totp_secret(encrypted: str, *, encryption_key: bytes) -> str:
    return decrypt_text(encrypted, encryption_key)


def totp_encryption_key(master_key: bytes) -> bytes:
    salt = b"keprix-totp-v1"
    return derive_key(base64.b64encode(master_key).decode("ascii"), salt)
