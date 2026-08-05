"""Persist and sync local disk folders into document indexes."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.documents.disk_paths import DEFAULT_EXTENSIONS, iter_disk_files, resolve_allowed_path
from keprix.documents.document_agent import get_document_agent
from keprix.documents.index_manager import get_index_manager


def _store_path() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "documents"
    except Exception:
        root = Path.home() / ".keprix" / "documents"
    root.mkdir(parents=True, exist_ok=True)
    return root / "disk_folders.json"


class DiskFolderStore:
    def __init__(self, store_path: Path | None = None) -> None:
        self._path = store_path or _store_path()
        self._folders: dict[str, dict[str, Any]] = {}
        if self._path.exists():
            for row in json.loads(self._path.read_text(encoding="utf-8")):
                self._folders[str(row["id"])] = row

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(list(self._folders.values()), indent=2),
            encoding="utf-8",
        )

    def list_folders(self, user_id: str) -> list[dict[str, Any]]:
        return [row for row in self._folders.values() if row.get("user_id") == user_id]

    def get(self, folder_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        row = self._folders.get(folder_id)
        if row is None:
            return None
        if user_id is not None and row.get("user_id") != user_id:
            return None
        return row

    def delete(self, folder_id: str, user_id: str) -> bool:
        row = self.get(folder_id, user_id)
        if row is None:
            return False
        self._folders.pop(folder_id, None)
        self._save()
        return True

    async def add_folder(
        self,
        *,
        user_id: str,
        path: str,
        name: str | None = None,
        index_id: str | None = None,
        recursive: bool = True,
        extensions: list[str] | None = None,
        also_import_workspace: bool = False,
    ) -> dict[str, Any]:
        folder = resolve_allowed_path(path)
        if not folder.is_dir():
            raise ValueError("Path must be a directory")
        if index_id:
            index = get_index_manager().get(index_id)
            if index is None:
                raise KeyError("index not found")
        else:
            index = get_document_agent().create_index(
                user_id=user_id,
                name=name or f"Disk: {folder.name}",
            )
            index_id = index.index_id
        folder_id = str(uuid.uuid4())
        row = {
            "id": folder_id,
            "user_id": user_id,
            "name": name or folder.name,
            "path": str(folder),
            "index_id": index_id,
            "recursive": bool(recursive),
            "extensions": list(extensions or DEFAULT_EXTENSIONS),
            "also_import_workspace": bool(also_import_workspace),
            "file_count": 0,
            "last_sync_at": None,
            "last_sync_error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._folders[folder_id] = row
        self._save()
        sync_result = await self.sync_folder(folder_id, user_id=user_id)
        row = self._folders[folder_id]
        row["initial_sync"] = sync_result
        return row

    async def sync_folder(self, folder_id: str, *, user_id: str) -> dict[str, Any]:
        row = self.get(folder_id, user_id)
        if row is None:
            raise KeyError("disk folder not found")
        folder = resolve_allowed_path(row["path"])
        if not folder.is_dir():
            raise ValueError("Configured folder path is missing or not a directory")
        files = iter_disk_files(
            folder,
            recursive=bool(row.get("recursive", True)),
            extensions=list(row.get("extensions") or DEFAULT_EXTENSIONS),
        )
        indexed = 0
        imported = 0
        errors: list[str] = []
        agent = get_document_agent()
        for path in files:
            try:
                content = path.read_bytes()
                try:
                    await agent.upload_and_index(
                        row["index_id"],
                        filename=str(path.relative_to(folder)),
                        content=content,
                    )
                    indexed += 1
                except Exception as exc:
                    errors.append(f"{path.name} (index): {exc}")
                if row.get("also_import_workspace"):
                    try:
                        from keprix.documents.disk_paths import read_path_as_text
                        from keprix.workspace.documents_pg import _use_db, pg_create_document
                        from keprix.workspace.repository import workspace_repo

                        title, text = read_path_as_text(path)
                        payload = {
                            "title": title,
                            "content": text,
                            "format": "markdown",
                            "tags": ["disk", "imported"],
                            "folder": row.get("name") or folder.name,
                        }
                        if _use_db():
                            await pg_create_document(user_id, payload)
                        else:
                            workspace_repo.create_document(
                                {"id": user_id, "username": user_id}, **payload
                            )
                        imported += 1
                    except Exception as exc:
                        errors.append(f"{path.name} (library): {exc}")
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
        row["file_count"] = indexed
        row["last_sync_at"] = datetime.now(timezone.utc).isoformat()
        row["last_sync_error"] = "; ".join(errors[:5]) if errors else None
        self._folders[folder_id] = row
        self._save()
        return {
            "folder_id": folder_id,
            "indexed": indexed,
            "imported_workspace": imported,
            "errors": errors[:20],
            "path": str(folder),
            "index_id": row["index_id"],
        }


_store: DiskFolderStore | None = None


def get_disk_folder_store() -> DiskFolderStore:
    global _store
    if _store is None:
        _store = DiskFolderStore()
    return _store
