"""Full install backup and restore."""

from __future__ import annotations

import json
import shutil
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from keprix.installer.paths import get_backup_dir, get_install_root


def _safe_members(members: Iterable[tarfile.TarInfo]) -> list[tarfile.TarInfo]:
    safe: list[tarfile.TarInfo] = []
    for member in members:
        if member.name.startswith("/") or ".." in Path(member.name).parts:
            raise ValueError(f"Unsafe archive path: {member.name}")
        safe.append(member)
    return safe


def create_backup(
    *,
    env_file: Path,
    data_dir: Path | None = None,
    identity_dir: Path | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Create keprix-backup-{timestamp}.tar.gz with env, data, and identity."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = output_dir or get_backup_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_path = out_dir / f"keprix-backup-{stamp}.tar.gz"

    data_dir = data_dir or Path("/data/keprix")
    identity_dir = identity_dir or Path.home() / ".keprix"

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "components": [],
    }

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "stage"
        stage.mkdir()

        if env_file.exists():
            shutil.copy2(env_file, stage / ".env")
            manifest["components"].append(".env")

        if data_dir.exists():
            shutil.copytree(data_dir, stage / "data", dirs_exist_ok=True)
            manifest["components"].append("data")

        if identity_dir.exists():
            shutil.copytree(identity_dir, stage / "identity", dirs_exist_ok=True)
            manifest["components"].append("identity")

        (stage / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(stage, arcname=".")

    return archive_path


def verify_backup(archive_path: Path) -> bool:
    if not archive_path.exists():
        return False
    with tarfile.open(archive_path, "r:gz") as archive:
        members = _safe_members(archive.getmembers())
        return any(member.name.endswith("MANIFEST.json") for member in members)


def restore_backup(
    archive_path: Path,
    *,
    env_file: Path,
    data_dir: Path | None = None,
    identity_dir: Path | None = None,
) -> None:
    if not verify_backup(archive_path):
        raise ValueError("Invalid backup archive")

    data_dir = data_dir or Path("/data/keprix")
    identity_dir = identity_dir or Path.home() / ".keprix"

    with tempfile.TemporaryDirectory() as tmp:
        extract_root = Path(tmp) / "extract"
        extract_root.mkdir()
        with tarfile.open(archive_path, "r:gz") as archive:
            archive.extractall(extract_root, members=_safe_members(archive.getmembers()))

        stage = extract_root
        for candidate in (extract_root, extract_root / "stage"):
            if (candidate / "MANIFEST.json").exists() or any(
                p.name == "MANIFEST.json" for p in candidate.rglob("MANIFEST.json")
            ):
                stage = candidate
                break

        env_src = stage / ".env"
        if not env_src.exists():
            env_src = next(stage.rglob(".env"), env_src)
        if env_src.exists():
            env_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(env_src, env_file)

        data_src = stage / "data"
        if data_src.exists():
            if data_dir.exists():
                shutil.rmtree(data_dir)
            shutil.copytree(data_src, data_dir)

        identity_src = stage / "identity"
        if identity_src.exists():
            if identity_dir.exists():
                shutil.rmtree(identity_dir)
            shutil.copytree(identity_src, identity_dir)
