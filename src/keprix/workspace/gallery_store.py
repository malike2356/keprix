"""Persistent gallery media library (filesystem + JSON index)."""

from __future__ import annotations

import json
import os
import re
import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_INDEX_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def gallery_root() -> Path:
    base = Path(os.environ.get("KEPRIX_DATA_DIR", "/tmp/keprix-data"))
    path = base / "gallery"
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_gallery_dir(user_id: str) -> Path:
    path = gallery_root() / re.sub(r"[^a-zA-Z0-9._-]+", "_", user_id or "local")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _index_path(user_id: str) -> Path:
    return user_gallery_dir(user_id) / "index.json"


def _load_index(user_id: str) -> dict[str, Any]:
    path = _index_path(user_id)
    if not path.is_file():
        return {"items": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"items": {}}
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, dict):
        return {"items": {}}
    return {"items": items}


def _save_index(user_id: str, index: dict[str, Any]) -> None:
    path = _index_path(user_id)
    path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")


def _file_for_id(user_id: str, image_id: str) -> Path | None:
    directory = user_gallery_dir(user_id)
    for path in directory.glob(f"{image_id}.*"):
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            return path
    # Legacy flat gallery (no user folder)
    for path in gallery_root().glob(f"{image_id}.*"):
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            return path
    return None


def _default_item(path: Path, *, user_id: str) -> dict[str, Any]:
    stat = path.stat()
    return {
        "id": path.stem,
        "filename": path.name,
        "original_name": path.name,
        "title": path.stem,
        "url": f"/api/workspace/gallery/{path.stem}/file",
        "size_bytes": stat.st_size,
        "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "updated_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "user_id": user_id,
        "tags": [],
        "folder": "",
        "favorite": False,
        "ocr_text": "",
        "ocr_at": None,
        "ocr_engine": None,
        "generation": None,
    }


def sync_index_from_disk(user_id: str) -> dict[str, Any]:
    """Reconcile index with files on disk (user dir + legacy flat files)."""
    with _INDEX_LOCK:
        index = _load_index(user_id)
        items: dict[str, Any] = dict(index.get("items") or {})
        seen: set[str] = set()

        candidates: list[Path] = []
        candidates.extend(
            p
            for p in user_gallery_dir(user_id).iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
        )
        # Legacy flat gallery (before per-user folders)
        for path in gallery_root().iterdir():
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                candidates.append(path)

        for path in candidates:
            item_id = path.stem
            seen.add(item_id)
            existing = items.get(item_id) if isinstance(items.get(item_id), dict) else None
            base = _default_item(path, user_id=user_id)
            if existing:
                base.update({k: v for k, v in existing.items() if k not in {"url", "size_bytes", "filename"}})
                base["filename"] = path.name
                base["url"] = f"/api/workspace/gallery/{item_id}/file"
                base["size_bytes"] = path.stat().st_size
            items[item_id] = base

        # Drop missing
        for item_id in list(items.keys()):
            if item_id not in seen and _file_for_id(user_id, item_id) is None:
                items.pop(item_id, None)

        index = {"items": items}
        _save_index(user_id, index)
        return index


def list_items(
    user_id: str,
    *,
    q: str = "",
    folder: str | None = None,
    favorites_only: bool = False,
) -> list[dict[str, Any]]:
    index = sync_index_from_disk(user_id)
    needle = (q or "").strip().lower()
    out: list[dict[str, Any]] = []
    for item in index["items"].values():
        if not isinstance(item, dict):
            continue
        if favorites_only and not item.get("favorite"):
            continue
        if folder is not None and folder != "":
            if str(item.get("folder") or "") != folder:
                continue
        if needle:
            hay = " ".join(
                [
                    str(item.get("title") or ""),
                    str(item.get("original_name") or ""),
                    str(item.get("filename") or ""),
                    str(item.get("folder") or ""),
                    " ".join(item.get("tags") or []),
                    str(item.get("ocr_text") or ""),
                    json.dumps(item.get("generation") or {}),
                ]
            ).lower()
            if needle not in hay:
                continue
        out.append(item)
    out.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return out


def folders_for_user(user_id: str) -> list[str]:
    items = list_items(user_id)
    names = sorted({str(i.get("folder") or "").strip() for i in items if str(i.get("folder") or "").strip()})
    return names


def get_item(user_id: str, image_id: str) -> dict[str, Any] | None:
    index = sync_index_from_disk(user_id)
    item = index["items"].get(image_id)
    return item if isinstance(item, dict) else None


def add_uploaded_file(
    user_id: str,
    *,
    source_name: str,
    suffix: str,
    file_obj: Any,
    generation: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    folder: str = "",
) -> dict[str, Any]:
    image_id = uuid.uuid4().hex
    dest = user_gallery_dir(user_id) / f"{image_id}{suffix}"
    with dest.open("wb") as handle:
        shutil.copyfileobj(file_obj, handle)
    item = _default_item(dest, user_id=user_id)
    item["original_name"] = Path(source_name or dest.name).name
    item["title"] = Path(source_name or dest.stem).stem
    item["tags"] = [t.strip() for t in (tags or []) if t and str(t).strip()]
    item["folder"] = (folder or "").strip()
    item["generation"] = generation
    item["created_at"] = _now()
    item["updated_at"] = item["created_at"]
    with _INDEX_LOCK:
        index = _load_index(user_id)
        index.setdefault("items", {})[image_id] = item
        _save_index(user_id, index)
    return item


def update_item(user_id: str, image_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    with _INDEX_LOCK:
        index = sync_index_from_disk(user_id)
        item = index["items"].get(image_id)
        if not isinstance(item, dict):
            raise KeyError(image_id)
        if "title" in patch and patch["title"] is not None:
            item["title"] = str(patch["title"]).strip() or item.get("title") or image_id
        if "folder" in patch and patch["folder"] is not None:
            item["folder"] = str(patch["folder"]).strip()
        if "favorite" in patch and patch["favorite"] is not None:
            item["favorite"] = bool(patch["favorite"])
        if "tags" in patch and patch["tags"] is not None:
            raw = patch["tags"]
            if isinstance(raw, str):
                tags = [p.strip() for p in raw.split(",") if p.strip()]
            else:
                tags = [str(p).strip() for p in raw if str(p).strip()]
            item["tags"] = tags
        if "generation" in patch and patch["generation"] is not None:
            item["generation"] = patch["generation"]
        if "ocr_text" in patch:
            item["ocr_text"] = str(patch.get("ocr_text") or "")
            item["ocr_at"] = patch.get("ocr_at") or _now()
            item["ocr_engine"] = patch.get("ocr_engine")
        item["updated_at"] = _now()
        index["items"][image_id] = item
        _save_index(user_id, index)
        return item


def delete_items(user_id: str, image_ids: list[str]) -> int:
    removed = 0
    with _INDEX_LOCK:
        index = sync_index_from_disk(user_id)
        for image_id in image_ids:
            path = _file_for_id(user_id, image_id)
            if path and path.is_file():
                path.unlink(missing_ok=True)
                removed += 1
            index["items"].pop(image_id, None)
        _save_index(user_id, index)
    return removed


def resolve_file(user_id: str, image_id: str) -> Path | None:
    return _file_for_id(user_id, image_id)


def run_image_ocr(path: Path) -> tuple[str, str]:
    """Return (text, engine). Raises RuntimeError with a clear message on failure."""
    enabled = os.environ.get("KEPRIX_OCR_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    if not enabled:
        raise RuntimeError("OCR is disabled. Set KEPRIX_OCR_ENABLED=true.")
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "OCR requires pytesseract and Pillow, plus the tesseract binary."
        ) from exc
    try:
        with Image.open(path) as image:
            text = pytesseract.image_to_string(image).strip()
    except Exception as exc:  # noqa: BLE001 - surface OCR toolchain errors
        raise RuntimeError(f"OCR failed: {exc}") from exc
    return text, "tesseract"
