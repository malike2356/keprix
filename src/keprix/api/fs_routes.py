"""Filesystem browser API used by /files (ported for the main API server)."""

from __future__ import annotations

import base64
import mimetypes
import os
import shutil
import stat
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/api/fs", tags=["filesystem"])

_FS_READDIR_HIDDEN = {
    ".git",
    ".hg",
    ".svn",
    ".cache",
    ".next",
    ".turbo",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "target",
    "venv",
}
_FS_DATA_URL_MAX_BYTES = 16 * 1024 * 1024
_FS_TEXT_SOURCE_MAX_BYTES = 64 * 1024 * 1024
_FS_TEXT_PREVIEW_MAX_BYTES = 512 * 1024
_FS_PREVIEW_LANGUAGE_BY_EXT = {
    ".c": "c",
    ".conf": "ini",
    ".cpp": "cpp",
    ".css": "css",
    ".csv": "csv",
    ".go": "go",
    ".graphql": "graphql",
    ".h": "c",
    ".hpp": "cpp",
    ".html": "html",
    ".java": "java",
    ".js": "javascript",
    ".json": "json",
    ".jsx": "jsx",
    ".kt": "kotlin",
    ".lua": "lua",
    ".md": "markdown",
    ".mjs": "javascript",
    ".py": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".sh": "shell",
    ".sql": "sql",
    ".svg": "xml",
    ".toml": "toml",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".txt": "text",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".zsh": "shell",
}
_FS_MIME_TYPES = {
    ".avi": "video/x-msvideo",
    ".bmp": "image/bmp",
    ".flac": "audio/flac",
    ".gif": "image/gif",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".m4a": "audio/mp4",
    ".mkv": "video/x-matroska",
    ".mov": "video/quicktime",
    ".mp3": "audio/mpeg",
    ".mp4": "video/mp4",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg; codecs=opus",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".wav": "audio/wav",
    ".webm": "video/webm",
    ".webp": "image/webp",
}


def _fs_path(raw_path: str) -> Path:
    raw = str(raw_path or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Path is required")
    if "\0" in raw:
        raise HTTPException(status_code=400, detail="Invalid path")
    try:
        if raw.lower().startswith("file:"):
            parsed = urllib.parse.urlparse(raw)
            if parsed.netloc and parsed.netloc not in {"", "localhost"}:
                raise ValueError
            raw = urllib.request.url2pathname(parsed.path)
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        return candidate.resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid path") from exc


def _fs_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in _FS_MIME_TYPES:
        return _FS_MIME_TYPES[suffix]
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "application/octet-stream"


def _fs_looks_binary(data: bytes) -> bool:
    if not data:
        return False
    if b"\0" in data:
        return True
    suspicious = sum(1 for byte in data if byte < 32 and byte not in {9, 10, 13})
    return suspicious / len(data) > 0.12


def _fs_regular_file(path: Path) -> tuple[Path, os.stat_result]:
    target = _fs_path(str(path))
    try:
        st = target.stat()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc
    except NotADirectoryError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="File is not readable") from exc
    except OSError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "Invalid path") from exc
    if stat.S_ISDIR(st.st_mode):
        raise HTTPException(status_code=400, detail="Path points to a directory")
    if not stat.S_ISREG(st.st_mode):
        raise HTTPException(status_code=400, detail="Only regular files can be read")
    return target, st


def _fs_find_git_root(start: Path) -> str | None:
    directory = start
    for _ in range(50):
        try:
            if (directory / ".git").exists():
                return str(directory)
        except OSError:
            return None
        parent = directory.parent
        if parent == directory:
            return None
        directory = parent
    return None


def _fs_default_cwd() -> str:
    candidates: list[str] = []
    for key in ("TERMINAL_CWD", "KEPRIX_DATA_DIR", "KEPRIX_HOME", "KEPRIX_WORKSPACE_ROOT"):
        value = os.environ.get(key, "").strip()
        if value and value not in {".", "auto", "cwd"}:
            candidates.append(value)
    candidates.extend(
        [
            "/data/keprix",
            "/home/keprix/.keprix",
            str(Path.home() / ".keprix"),
            str(Path.cwd()),
        ]
    )
    try:
        from keprix_cli.config import get_keprix_home, load_config

        cfg_terminal = (load_config().get("terminal") or {}) if callable(load_config) else {}
        raw = str(cfg_terminal.get("cwd") or "").strip()
        if raw:
            candidates.insert(0, raw)
        candidates.insert(0, str(get_keprix_home()))
    except Exception:
        pass
    seen: set[str] = set()
    for raw in candidates:
        if raw in seen:
            continue
        seen.add(raw)
        try:
            candidate = Path(raw).expanduser().resolve(strict=False)
            if candidate.is_dir():
                return str(candidate)
        except (OSError, RuntimeError):
            continue
    return str(Path.cwd())


def _fs_git_branch(cwd: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        return (result.stdout or "").strip()
    except Exception:
        return ""


def _entry_meta(path: Path, *, is_dir: bool) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "name": path.name or str(path),
        "path": str(path),
        "isDirectory": is_dir,
    }
    try:
        st = path.lstat()
        meta["size"] = int(st.st_size) if not is_dir else 0
        meta["mtime"] = st.st_mtime
        meta["modified_at"] = __import__("datetime").datetime.fromtimestamp(
            st.st_mtime, tz=__import__("datetime").timezone.utc
        ).isoformat()
    except OSError:
        pass
    return meta


class MkdirBody(BaseModel):
    path: str = Field(..., min_length=1)


class ImportDocsBody(BaseModel):
    path: str = Field(..., min_length=1)


@router.get("/list")
async def fs_list(path: str = Query(...), _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    target = _fs_path(path)
    try:
        entries = []
        with os.scandir(target) as scan:
            for entry in scan:
                if entry.name in _FS_READDIR_HIDDEN:
                    continue
                is_dir = entry.is_dir(follow_symlinks=False)
                entries.append(_entry_meta(Path(entry.path), is_dir=is_dir))
        entries.sort(key=lambda item: (not item["isDirectory"], item["name"].lower(), item["name"]))
        return {
            "entries": entries,
            "path": str(target),
            "count": len(entries),
        }
    except FileNotFoundError:
        return {"entries": [], "error": "ENOENT", "message": "Path not found", "path": str(target)}
    except NotADirectoryError:
        return {"entries": [], "error": "ENOTDIR", "message": "Not a directory", "path": str(target)}
    except PermissionError:
        return {"entries": [], "error": "EACCES", "message": "Permission denied", "path": str(target)}
    except OSError as exc:
        return {
            "entries": [],
            "error": getattr(exc, "strerror", None) or "read-error",
            "message": str(exc),
            "path": str(target),
        }


@router.get("/read-text")
async def fs_read_text(path: str = Query(...), _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    target, st = _fs_regular_file(_fs_path(path))
    if st.st_size > _FS_TEXT_SOURCE_MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large")
    bytes_to_read = min(st.st_size, _FS_TEXT_PREVIEW_MAX_BYTES)
    try:
        with target.open("rb") as handle:
            data = handle.read(bytes_to_read)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="File is not readable") from exc
    except OSError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "File read failed") from exc
    return {
        "binary": _fs_looks_binary(data[:4096]),
        "byteSize": st.st_size,
        "language": _FS_PREVIEW_LANGUAGE_BY_EXT.get(target.suffix.lower(), "text"),
        "mimeType": _fs_mime_type(target),
        "path": str(target),
        "text": data.decode("utf-8", errors="replace"),
        "truncated": st.st_size > _FS_TEXT_PREVIEW_MAX_BYTES,
    }


@router.get("/read-data-url")
async def fs_read_data_url(path: str = Query(...), _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    target, st = _fs_regular_file(_fs_path(path))
    if st.st_size > _FS_DATA_URL_MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large")
    try:
        encoded = base64.b64encode(target.read_bytes()).decode("ascii")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="File is not readable") from exc
    except OSError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "File read failed") from exc
    return {"dataUrl": f"data:{_fs_mime_type(target)};base64,{encoded}"}


@router.get("/git-root")
async def fs_git_root(path: str = Query(...), _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    target = _fs_path(path)
    try:
        st = target.stat()
        start = target if stat.S_ISDIR(st.st_mode) else target.parent
    except OSError:
        start = target
    return {"root": _fs_find_git_root(start)}


@router.get("/default-cwd")
async def fs_default_cwd(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    cwd = _fs_default_cwd()
    return {
        "cwd": cwd,
        "branch": _fs_git_branch(cwd),
        "shortcuts": {
            "data": os.environ.get("KEPRIX_DATA_DIR") or "/data/keprix",
            "home": os.environ.get("KEPRIX_HOME") or "/home/keprix/.keprix",
            "docs": str(Path(os.environ.get("KEPRIX_DATA_DIR") or "/data/keprix") / "docs"),
        },
    }


@router.post("/mkdir")
async def fs_mkdir(body: MkdirBody, _user: dict = Depends(require_admin)) -> dict[str, Any]:
    target = _fs_path(body.path)
    try:
        target.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="Directory is not writable") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not create directory: {exc}") from exc
    return {"ok": True, "path": str(target), "entry": _entry_meta(target, is_dir=True)}


@router.post("/upload")
async def fs_upload(
    path: str = Form(...),
    file: UploadFile = File(...),
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    directory = _fs_path(path)
    if directory.exists() and not directory.is_dir():
        raise HTTPException(400, "Upload path must be a directory")
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HTTPException(500, f"Could not create directory: {exc}") from exc
    name = Path(file.filename or "upload.bin").name
    target = directory / name
    try:
        with target.open("wb") as handle:
            shutil.copyfileobj(file.file, handle)
    except PermissionError as exc:
        raise HTTPException(403, "Directory is not writable") from exc
    except OSError as exc:
        raise HTTPException(500, f"Upload failed: {exc}") from exc
    return {"ok": True, "path": str(target), "entry": _entry_meta(target, is_dir=False)}


@router.post("/import-to-documents")
async def fs_import_to_documents(
    body: ImportDocsBody, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    from keprix.documents.disk_paths import read_path_as_text, resolve_allowed_path
    from keprix.workspace.document_helpers import document_to_dict
    from keprix.workspace.documents_pg import _use_db, pg_create_document
    from keprix.workspace.repository import workspace_repo

    try:
        # Prefer documents allowed roots; fall back to any readable absolute file for admins.
        try:
            path = resolve_allowed_path(body.path)
        except ValueError:
            path = _fs_path(body.path)
        if not path.is_file():
            raise ValueError("Path must be a file")
        title, content = read_path_as_text(path)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    uid = str(user.get("id") or user.get("username") or "local")
    payload = {
        "title": title,
        "content": content,
        "format": "markdown",
        "tags": ["files", "imported"],
        "folder": "files",
    }
    if _use_db():
        doc = await pg_create_document(uid, payload)
        if doc is None:
            raise HTTPException(500, "Failed to persist document")
    else:
        doc = workspace_repo.create_document(user, **payload)
    return document_to_dict(doc)
