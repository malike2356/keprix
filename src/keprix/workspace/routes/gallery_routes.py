"""Workspace image gallery / media library routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.workspace import gallery_store

router = APIRouter(prefix="/api/workspace/gallery", tags=["workspace-gallery"])


def _uid(user: dict) -> str:
    return str(user.get("id") or user.get("username") or "local")


class GalleryPatch(BaseModel):
    title: str | None = None
    folder: str | None = None
    favorite: bool | None = None
    tags: list[str] | str | None = None
    generation: dict[str, Any] | None = None


class BulkDeleteBody(BaseModel):
    ids: list[str] = Field(default_factory=list)


@router.get("")
async def list_gallery(
    q: str = Query(""),
    folder: str | None = Query(None),
    favorites: bool = Query(False),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    uid = _uid(user)
    items = gallery_store.list_items(uid, q=q, folder=folder, favorites_only=favorites)
    return {
        "items": items,
        "folders": gallery_store.folders_for_user(uid),
        "count": len(items),
    }


@router.post("/upload")
async def upload_gallery_image(
    file: UploadFile = File(...),
    folder: str = Form(""),
    tags: str = Form(""),
    generation_json: str = Form(""),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported")
    suffix = Path(file.filename or "upload.png").suffix.lower() or ".png"
    if suffix not in gallery_store.IMAGE_SUFFIXES:
        raise HTTPException(status_code=400, detail="Unsupported image type")
    tag_list = [p.strip() for p in tags.split(",") if p.strip()]
    generation = None
    if generation_json.strip():
        import json

        try:
            generation = json.loads(generation_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="generation_json must be valid JSON") from exc
    item = gallery_store.add_uploaded_file(
        _uid(user),
        source_name=file.filename or f"upload{suffix}",
        suffix=suffix,
        file_obj=file.file,
        generation=generation if isinstance(generation, dict) else None,
        tags=tag_list,
        folder=folder,
    )
    return {"item": item}


@router.get("/{image_id}")
async def get_gallery_item(image_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    item = gallery_store.get_item(_uid(user), image_id)
    if not item:
        raise HTTPException(status_code=404, detail="Image not found")
    return {"item": item}


@router.patch("/{image_id}")
async def patch_gallery_item(
    image_id: str,
    body: GalleryPatch,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        item = gallery_store.update_item(_uid(user), image_id, body.model_dump(exclude_unset=True))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Image not found") from exc
    return {"item": item}


@router.post("/{image_id}/ocr")
async def ocr_gallery_item(image_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    import asyncio

    uid = _uid(user)
    path = gallery_store.resolve_file(uid, image_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Image not found")
    try:
        text, engine = await asyncio.to_thread(gallery_store.run_image_ocr, path)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    item = gallery_store.update_item(
        uid,
        image_id,
        {"ocr_text": text, "ocr_engine": engine},
    )
    # Also land OCR text into unified memory recall path.
    try:
        from keprix.memory.episodic.store import create_episodic_store

        await create_episodic_store().save(
            uid,
            text,
            metadata={
                "tags": ["gallery", "ocr", "multimodal"],
                "memory_type": "semantic",
                "modality": "image_ocr",
                "source": "gallery_ocr",
                "belief_state": "active",
                "confidence": 0.7,
                "model_side": "user",
                "gallery_image_id": image_id,
            },
        )
    except Exception:
        pass
    return {"item": item, "text": text, "engine": engine}


@router.post("/{image_id}/import-to-documents")
async def import_gallery_to_documents(
    image_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    from keprix.workspace.document_helpers import document_to_dict
    from keprix.workspace.documents_pg import _use_db, pg_create_document
    from keprix.workspace.repository import workspace_repo

    uid = _uid(user)
    item = gallery_store.get_item(uid, image_id)
    if not item:
        raise HTTPException(status_code=404, detail="Image not found")
    text = str(item.get("ocr_text") or "").strip()
    if not text:
        import asyncio

        path = gallery_store.resolve_file(uid, image_id)
        if path is None:
            raise HTTPException(status_code=404, detail="Image file missing")
        try:
            text, engine = await asyncio.to_thread(gallery_store.run_image_ocr, path)
            item = gallery_store.update_item(
                uid, image_id, {"ocr_text": text, "ocr_engine": engine}
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not text.strip():
        raise HTTPException(status_code=400, detail="OCR produced no text to import")
    title = str(item.get("title") or item.get("original_name") or image_id)
    payload = {
        "title": f"{title} (OCR)",
        "content": text,
        "format": "markdown",
        "tags": list({*(item.get("tags") or []), "gallery", "ocr"}),
        "folder": str(item.get("folder") or "gallery"),
    }
    if _use_db():
        doc = await pg_create_document(uid, payload)
        if doc is None:
            raise HTTPException(status_code=500, detail="Failed to persist document")
    else:
        doc = workspace_repo.create_document(user, **payload)
    return {"document": document_to_dict(doc), "item": item}


@router.post("/bulk-delete")
async def bulk_delete_gallery(
    body: BulkDeleteBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ids = [i for i in body.ids if i]
    if not ids:
        raise HTTPException(status_code=400, detail="No ids provided")
    removed = gallery_store.delete_items(_uid(user), ids)
    return {"ok": True, "removed": removed}


@router.get("/{image_id}/file")
async def get_gallery_file(image_id: str, user: dict = Depends(get_current_user)) -> FileResponse:
    path = gallery_store.resolve_file(_uid(user), image_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)


@router.delete("/{image_id}")
async def delete_gallery_image(image_id: str, user: dict = Depends(get_current_user)) -> dict[str, bool]:
    before = gallery_store.get_item(_uid(user), image_id) or gallery_store.resolve_file(_uid(user), image_id)
    if not before:
        raise HTTPException(status_code=404, detail="Image not found")
    gallery_store.delete_items(_uid(user), [image_id])
    return {"ok": True}
