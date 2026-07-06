"""Tests for hot backup archives."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from keprix.workspace.hot_backup import (
    DEFAULT_EXCLUDE_DIRS,
    build_manifest,
    collect_backup_paths,
    create_hot_backup,
    verify_hot_backup,
)


def test_create_and_verify_hot_backup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("keprix.workspace.hot_backup.collect_backup_paths", lambda: [])
    sample = tmp_path / "sample.txt"
    sample.write_text("hello backup", encoding="utf-8")
    archive = tmp_path / "backup.tar.gz"

    meta = create_hot_backup(archive, extra_paths=[sample])
    assert meta["file_count"] >= 1
    assert archive.exists()

    result = verify_hot_backup(archive)
    assert result["ok"] is True


def test_manifest_checksums(tmp_path: Path) -> None:
    file_a = tmp_path / "a.txt"
    file_a.write_text("a", encoding="utf-8")
    manifest = build_manifest([file_a], archive_name="test.tar.gz")
    assert manifest["file_count"] == 1
    assert len(manifest["files"][0]["sha256"]) == 64


def test_collect_backup_paths_excludes_default_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    (tmp_path / "auth.json").write_text("{}", encoding="utf-8")
    (tmp_path / "research").mkdir()
    (tmp_path / "research" / "report.md").write_text("x", encoding="utf-8")
    (tmp_path / "sessions").mkdir()
    (tmp_path / "sessions" / "s.json").write_text("{}", encoding="utf-8")

    paths = collect_backup_paths()
    rel_names = {path.name for path in paths}
    assert "auth.json" in rel_names
    assert "report.md" not in rel_names
    assert "s.json" not in rel_names
    assert DEFAULT_EXCLUDE_DIRS == frozenset({"research", "mail-attachments", "sessions"})


def test_verify_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.tar.gz"

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo(name="../../etc/passwd")
        info.size = 4
        tar.addfile(info, io.BytesIO(b"evil"))
    archive.write_bytes(buf.getvalue())

    result = verify_hot_backup(archive)
    assert result["ok"] is False
    assert any("unsafe" in error for error in result["errors"])

