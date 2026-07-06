"""Backup archive creation and restore."""

from __future__ import annotations

import io
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from keprix.auth.config import data_dir
from keprix.security.crypto import decrypt_aes_gcm, derive_key, encrypt_aes_gcm


class BackupService:
    def __init__(self, backup_dir: str | None = None) -> None:
        root = Path(data_dir()) / "backups"
        root.mkdir(parents=True, exist_ok=True)
        self.backup_dir = Path(backup_dir or root)

    def create_backup(self, *, password: str | None = None) -> dict[str, Any]:
        from keprix.workspace.hot_backup import create_hot_backup

        backup_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"keprix_hot_{timestamp}.tar.gz"
        path = self.backup_dir / filename

        meta = create_hot_backup(path, password=password)
        record = {
            "id": backup_id,
            "filename": path.name,
            "path": str(path),
            "created_at": meta["created_at"],
            "encrypted": meta["encrypted"],
            "size_bytes": meta["size_bytes"],
            "format": "tar.gz",
            "file_count": meta["file_count"],
        }
        index_path = self.backup_dir / "index.json"
        index = []
        if index_path.exists():
            index = json.loads(index_path.read_text(encoding="utf-8"))
        index.append(record)
        index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
        return record

    def list_backups(self) -> list[dict[str, Any]]:
        index_path = self.backup_dir / "index.json"
        if not index_path.exists():
            return []
        return json.loads(index_path.read_text(encoding="utf-8"))

    def get_backup_path(self, backup_id: str) -> Path | None:
        for item in self.list_backups():
            if item.get("id") == backup_id:
                return Path(item["path"])
        return None

    def delete_backup(self, backup_id: str) -> bool:
        path = self.get_backup_path(backup_id)
        if path is None:
            return False
        if path.exists():
            path.unlink()
        remaining = [item for item in self.list_backups() if item.get("id") != backup_id]
        (self.backup_dir / "index.json").write_text(json.dumps(remaining, indent=2), encoding="utf-8")
        return True

    def restore_backup(self, archive_bytes: bytes, *, password: str | None = None) -> dict[str, Any]:
        if archive_bytes[:2] == b"PK":
            return self._restore_legacy_zip(archive_bytes, password=password)

        from keprix.workspace.hot_backup import restore_hot_backup

        result = restore_hot_backup(archive_bytes, password=password)
        return {
            "ok": result["ok"],
            "restored_at": result.get("restored_at", datetime.now(timezone.utc).isoformat()),
            "restored_files": result.get("restored_files", 0),
        }

    def _restore_legacy_zip(self, archive_bytes: bytes, *, password: str | None = None) -> dict[str, Any]:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            payload_bytes = archive.read("backup.bin")
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))

        if manifest.get("encrypted"):
            if not password:
                raise ValueError("Backup password required")
            salt, encrypted = payload_bytes[:16], payload_bytes[16:]
            key = derive_key(password, salt)
            payload_bytes = decrypt_aes_gcm(encrypted, key)

        payload = json.loads(payload_bytes.decode("utf-8"))
        self._apply_payload(payload)
        return {"ok": True, "restored_at": datetime.now(timezone.utc).isoformat()}

    def _collect_payload(self) -> dict[str, Any]:
        base = Path(data_dir())
        files: dict[str, str] = {}
        for name in ("auth.json", "sessions.json", "audit_log.jsonl"):
            path = base / name
            if path.exists():
                files[name] = path.read_text(encoding="utf-8")
        return {
            "version": 1,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "files": files,
        }

    def _apply_payload(self, payload: dict[str, Any]) -> None:
        base = Path(data_dir())
        base.mkdir(parents=True, exist_ok=True)
        for name, content in (payload.get("files") or {}).items():
            (base / name).write_text(content, encoding="utf-8")


backup_service = BackupService()
