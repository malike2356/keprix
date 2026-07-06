"""Backup archive creation and restore."""

from __future__ import annotations

from pathlib import Path

from keprix.installer.backup import create_backup, restore_backup, verify_backup


def test_backup_restore_roundtrip(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("KEPRIX_VERSION=0.1.0\nKEPRIX_ADMIN_PASSWORD=secret\n", encoding="utf-8")

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "note.txt").write_text("hello", encoding="utf-8")

    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    (identity_dir / "dev.json").write_text("{}", encoding="utf-8")

    archive = create_backup(
        env_file=env_file,
        data_dir=data_dir,
        identity_dir=identity_dir,
        output_dir=tmp_path / "backups",
    )
    assert archive.exists()
    assert verify_backup(archive)

    env_file.write_text("KEPRIX_VERSION=broken\n", encoding="utf-8")
    if data_dir.exists():
        for child in data_dir.iterdir():
            child.unlink()
    if identity_dir.exists():
        for child in identity_dir.iterdir():
            child.unlink()

    restore_backup(archive, env_file=env_file, data_dir=data_dir, identity_dir=identity_dir)
    assert "KEPRIX_ADMIN_PASSWORD=secret" in env_file.read_text(encoding="utf-8")
    assert (data_dir / "note.txt").read_text(encoding="utf-8") == "hello"
    assert (identity_dir / "dev.json").exists()
