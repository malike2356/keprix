"""Cryptographic helpers for auth, vault, and TOTP."""

from __future__ import annotations

import base64
import hashlib
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


PBKDF2_ITERATIONS = 600_000


def derive_key(password: str, salt: bytes, *, iterations: int = PBKDF2_ITERATIONS) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_aes_gcm(plaintext: bytes, key: bytes, *, aad: bytes | None = None) -> bytes:
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, aad)
    return nonce + ciphertext


def decrypt_aes_gcm(payload: bytes, key: bytes, *, aad: bytes | None = None) -> bytes:
    nonce, ciphertext = payload[:12], payload[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, aad)


def encrypt_text(value: str, key: bytes) -> str:
    encrypted = encrypt_aes_gcm(value.encode("utf-8"), key)
    return base64.b64encode(encrypted).decode("ascii")


def decrypt_text(value: str, key: bytes) -> str:
    payload = base64.b64decode(value.encode("ascii"))
    return decrypt_aes_gcm(payload, key).decode("utf-8")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def zero_bytes(data: bytearray) -> None:
    for idx in range(len(data)):
        data[idx] = 0
