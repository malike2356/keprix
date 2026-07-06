"""Ed25519 signing for hub agent and tool packages."""

from __future__ import annotations

import json
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_pem_private_key,
    load_pem_public_key,
)


def _signing_key_path() -> Path:
    return Path(os.environ.get("KEPRIX_HUB_SIGNING_KEY", Path.home() / ".keprix" / "hub" / "package-signing-key.pem"))


def _verify_key_path() -> Path:
    return Path(os.environ.get("KEPRIX_HUB_VERIFY_KEY", Path.home() / ".keprix" / "hub" / "package-verify-key.pem"))


def ensure_signing_keys() -> tuple[Path, Path]:
    private_path = _signing_key_path()
    public_path = _verify_key_path()
    if private_path.exists() and public_path.exists():
        return private_path, public_path
    private_path.parent.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    private_path.write_bytes(private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
    public_path.write_bytes(private_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))
    return private_path, public_path


def package_payload(name: str, version: str, manifest: dict) -> bytes:
    return json.dumps({"name": name, "version": version, "manifest": manifest}, sort_keys=True).encode()


def sign_package(name: str, version: str, manifest: dict) -> str:
    private_path, _ = ensure_signing_keys()
    private_key = load_pem_private_key(private_path.read_bytes(), password=None)
    return private_key.sign(package_payload(name, version, manifest)).hex()


def verify_package(name: str, version: str, manifest: dict, signature_hex: str) -> bool:
    try:
        _, public_path = ensure_signing_keys()
        public_key = load_pem_public_key(public_path.read_bytes())
        public_key.verify(bytes.fromhex(signature_hex), package_payload(name, version, manifest))
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False
