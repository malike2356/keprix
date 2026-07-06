"""Safe zip extraction and install helpers for agent app bundles."""

from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from keprix.agent_apps.app_manifest import ManifestValidationError, load_manifest, validate_manifest

DEFAULT_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
FORBIDDEN_ZIP_NAMES = {".env", ".git", "__pycache__", ".venv", "venv", "node_modules"}


def max_upload_bytes() -> int:
    raw = os.environ.get("KEPRIX_AGENT_APP_MAX_UPLOAD_BYTES", "").strip()
    if raw.isdigit():
        return int(raw)
    return DEFAULT_MAX_UPLOAD_BYTES


def _is_safe_zip_member(name: str) -> bool:
    normalized = Path(name)
    if normalized.is_absolute():
        return False
    if ".." in normalized.parts:
        return False
    if any(part in FORBIDDEN_ZIP_NAMES for part in normalized.parts):
        return False
    if normalized.name.startswith(".env"):
        return False
    return True


def extract_zip_bundle(zip_path: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    resolved_dest = dest_dir.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            if not _is_safe_zip_member(member.filename):
                raise ManifestValidationError(f"Unsafe zip entry: {member.filename}")
            target = (dest_dir / member.filename).resolve()
            if not str(target).startswith(str(resolved_dest)):
                raise ManifestValidationError(f"Path traversal detected in zip: {member.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as handle:
                shutil.copyfileobj(source, handle)


def resolve_app_root(extract_dir: Path) -> Path:
    if (extract_dir / "agent.yaml").exists():
        return extract_dir
    candidates = [child for child in extract_dir.iterdir() if child.is_dir()]
    with_manifest = [child for child in candidates if (child / "agent.yaml").exists()]
    if len(with_manifest) == 1:
        return with_manifest[0]
    if len(with_manifest) > 1:
        raise ManifestValidationError("Zip bundle contains multiple agent app folders")
    raise ManifestValidationError("Zip bundle does not contain agent.yaml")


def validate_bundle_dir(source_dir: Path) -> dict:
    manifest = load_manifest(source_dir)
    validate_manifest(manifest)
    return {"valid": True, "manifest": manifest.summary_dict()}


def prepare_uploaded_bundle(zip_bytes: bytes) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
    if len(zip_bytes) > max_upload_bytes():
        raise ManifestValidationError(
            f"Bundle exceeds max upload size ({max_upload_bytes()} bytes)",
        )
    temp_root = tempfile.TemporaryDirectory(prefix="keprix-agent-app-upload-")
    zip_path = Path(temp_root.name) / "upload.zip"
    zip_path.write_bytes(zip_bytes)
    extract_dir = Path(temp_root.name) / "extracted"
    extract_zip_bundle(zip_path, extract_dir)
    app_root = resolve_app_root(extract_dir)
    validate_bundle_dir(app_root)
    return app_root, temp_root


def validate_uploaded_zip(zip_bytes: bytes) -> dict:
    app_root, temp_root = prepare_uploaded_bundle(zip_bytes)
    try:
        return validate_bundle_dir(app_root)
    finally:
        temp_root.cleanup()
