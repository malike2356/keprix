"""Ed25519 signing for generated tools."""

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
    return Path(os.environ.get("KEPRIX_TOOL_SIGNING_KEY", Path.home() / ".keprix" / "mutation" / "tool-signing-key.pem"))


def _verify_key_path() -> Path:
    return Path(os.environ.get("KEPRIX_TOOL_VERIFY_KEY", Path.home() / ".keprix" / "mutation" / "tool-verify-key.pem"))


def ensure_signing_keys() -> tuple[Path, Path]:
    private_path = _signing_key_path()
    public_path = _verify_key_path()
    if private_path.exists() and public_path.exists():
        return private_path, public_path
    private_path.parent.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    public_bytes = private_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    private_path.write_bytes(private_bytes)
    public_path.write_bytes(public_bytes)
    return private_path, public_path


def _payload(tool_name: str, tool_code: str, metadata: dict) -> bytes:
    return json.dumps({"name": tool_name, "code": tool_code, "meta": metadata}, sort_keys=True).encode()


def sign_tool(tool_name: str, tool_code: str, metadata: dict | None = None) -> str:
    private_path, _ = ensure_signing_keys()
    private_key = load_pem_private_key(private_path.read_bytes(), password=None)
    sig_bytes = private_key.sign(_payload(tool_name, tool_code, metadata or {}))
    return sig_bytes.hex()


def verify_tool(tool_name: str, tool_code: str, signature_hex: str, metadata: dict | None = None) -> bool:
    try:
        _, public_path = ensure_signing_keys()
        public_key = load_pem_public_key(public_path.read_bytes())
        public_key.verify(bytes.fromhex(signature_hex), _payload(tool_name, tool_code, metadata or {}))
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False
