"""Hot backup: tar.gz archives with MANIFEST and sha256 checksums."""

from __future__ import annotations

import hashlib
import json
import os
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from keprix.auth.config import data_dir

BACKUP_VERSION = 2
MANIFEST_NAME = "MANIFEST.json"
DEFAULT_EXCLUDE_DIRS = frozenset({"research", "mail-attachments", "sessions"})


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_unsafe_tar_member(name: str) -> bool:
    if not name or name.startswith("/"):
        return True
    return ".." in Path(name).parts


def _should_exclude_backup_path(path: Path) -> bool:
    return any(part in DEFAULT_EXCLUDE_DIRS for part in path.parts)


def collect_backup_paths() -> list[Path]:
    """Collect files to include in a hot backup archive."""
    roots: list[Path] = []
    base = Path(data_dir())
    if base.exists():
        roots.append(base)
    try:
        from keprix_cli.config import get_keprix_home

        home = Path(get_keprix_home())
        if home.exists() and home != base:
            roots.append(home)
    except Exception:
        home = Path.home() / ".keprix"
        if home.exists() and home not in roots:
            roots.append(home)

    files: list[Path] = []
    seen: set[Path] = set()
    skip_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv"}
    for root in roots:
        if root.is_file():
            resolved = root.resolve()
            if resolved not in seen:
                seen.add(resolved)
                files.append(resolved)
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in skip_dirs for part in path.parts):
                continue
            if _should_exclude_backup_path(path):
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(resolved)
    return sorted(files)


def build_manifest(files: Iterable[Path], *, archive_name: str) -> dict[str, Any]:
    file_list = list(files)
    entries: list[dict[str, Any]] = []
    for path in file_list:
        rel = path.name if len(file_list) == 1 else str(path)
        try:
            from keprix_cli.config import get_keprix_home

            home = Path(get_keprix_home()).resolve()
            if path.is_relative_to(home):
                rel = str(path.relative_to(home))
        except Exception:
            rel = str(path)
        entries.append(
            {
                "path": rel,
                "size_bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
        )
    return {
        "format": "keprix-hot-backup",
        "version": BACKUP_VERSION,
        "archive": archive_name,
        "created_at": _utcnow(),
        "file_count": len(entries),
        "files": entries,
    }


def create_hot_backup(
    output_path: Path,
    *,
    password: str | None = None,
    extra_paths: Iterable[Path] | None = None,
) -> dict[str, Any]:
    """Create a tar.gz backup with embedded MANIFEST.json."""
    files = collect_backup_paths()
    if extra_paths:
        files.extend(Path(p).resolve() for p in extra_paths if Path(p).is_file())
        files = sorted(set(files))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(files, archive_name=output_path.name)

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        manifest_path = tmp_dir / MANIFEST_NAME
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        with tarfile.open(output_path, "w:gz") as archive:
            archive.add(manifest_path, arcname=MANIFEST_NAME)
            for path in files:
                try:
                    from keprix_cli.config import get_keprix_home

                    home = Path(get_keprix_home()).resolve()
                    arcname = str(path.relative_to(home)) if path.is_relative_to(home) else path.name
                except Exception:
                    arcname = path.name
                archive.add(path, arcname=f"data/{arcname}")

    if password:
        from keprix.security.crypto import derive_key, encrypt_aes_gcm

        raw = output_path.read_bytes()
        salt = os.urandom(16)
        key = derive_key(password, salt)
        encrypted = encrypt_aes_gcm(raw, key)
        enc_path = output_path.with_suffix(output_path.suffix + ".enc")
        enc_path.write_bytes(salt + encrypted)
        output_path.unlink()
        output_path = enc_path
        manifest["encrypted"] = True
    else:
        manifest["encrypted"] = False

    return {
        "path": str(output_path),
        "filename": output_path.name,
        "created_at": manifest["created_at"],
        "size_bytes": output_path.stat().st_size,
        "file_count": manifest["file_count"],
        "encrypted": manifest["encrypted"],
        "format": "tar.gz",
    }


def restore_hot_backup(
    archive_bytes: bytes,
    *,
    password: str | None = None,
) -> dict[str, Any]:
    """Extract a hot backup archive back into KEPRIX_HOME and data_dir."""
    import io

    payload = archive_bytes
    if payload[:2] != b"\x1f\x8b":
        if not password:
            raise ValueError("Backup password required")
        from keprix.security.crypto import decrypt_aes_gcm, derive_key

        salt, encrypted = payload[:16], payload[16:]
        key = derive_key(password, salt)
        payload = decrypt_aes_gcm(encrypted, key)

    base = Path(data_dir())
    try:
        from keprix_cli.config import get_keprix_home

        home = Path(get_keprix_home()).resolve()
    except Exception:
        home = Path.home() / ".keprix"

    restored = 0
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        for member in archive.getmembers():
            if _is_unsafe_tar_member(member.name):
                raise ValueError(f"Unsafe archive path: {member.name}")
            if not member.isfile() or member.name == MANIFEST_NAME:
                continue
            if not member.name.startswith("data/"):
                continue
            rel = member.name[len("data/") :]
            dest = (base / rel) if (base / rel).parent.exists() or "/" not in rel else (home / rel)
            if not str(dest).startswith(str(base)) and not str(dest).startswith(str(home)):
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            extracted = archive.extractfile(member)
            if extracted is None:
                continue
            dest.write_bytes(extracted.read())
            restored += 1

    return {
        "ok": True,
        "restored_files": restored,
        "restored_at": _utcnow(),
    }


def verify_hot_backup(archive_path: Path) -> dict[str, Any]:
    """Verify MANIFEST checksums inside a hot backup archive."""
    import tempfile

    errors: list[str] = []
    checked = 0
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            if _is_unsafe_tar_member(member.name):
                return {"ok": False, "checked": 0, "errors": [f"unsafe path: {member.name}"]}
        with tempfile.TemporaryDirectory() as tmp:
            archive.extract(MANIFEST_NAME, path=tmp)
            manifest = json.loads((Path(tmp) / MANIFEST_NAME).read_text(encoding="utf-8"))
            for entry in manifest.get("files", []):
                member_name = f"data/{entry['path']}"
                try:
                    archive.extract(member_name, path=tmp)
                    actual = _sha256_file(Path(tmp) / member_name)
                    if actual != entry["sha256"]:
                        errors.append(f"checksum mismatch: {entry['path']}")
                    checked += 1
                except KeyError:
                    errors.append(f"missing: {entry['path']}")
    return {"ok": not errors, "checked": checked, "errors": errors}
