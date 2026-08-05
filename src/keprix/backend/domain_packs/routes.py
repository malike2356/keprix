"""Domain pack HTTP routes (Prompt 30)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from keprix.backend.domain_packs.ingestion import ingest_sources
from keprix.backend.domain_packs.localization import apply_localization, sync_glossary_to_localization
from keprix.backend.domain_packs.manifests import create_manifest_from_template
from keprix.backend.domain_packs.publisher import bump_version, publish_to_hub
from keprix.backend.domain_packs.schemas import DomainPackManifest, GlossaryTerm, PackSource
from keprix.backend.domain_packs.store import get_domain_pack_store
from keprix.backend.domain_packs.validation import validate_pack
from keprix.review_gateway.service import create_review_request

router = APIRouter(prefix="/api/domain-packs", tags=["domain-packs"])


class CreatePackBody(BaseModel):
    domain_name: str = Field(min_length=1)
    jurisdictions: list[str] = Field(default_factory=list)


class UpdatePackBody(BaseModel):
    jurisdictions: list[str] | None = None
    glossary: list[dict[str, Any]] | None = None
    common_tasks: list[str] | None = None
    playbooks: list[dict[str, str]] | None = None
    disclaimers: list[str] | None = None
    limitations: list[str] | None = None
    can_do: list[str] | None = None
    cannot_do: list[str] | None = None
    data_schemas: list[dict[str, Any]] | None = None
    tool_permissions: list[str] | None = None
    sources: list[dict[str, Any]] | None = None


class IngestBody(BaseModel):
    sources: list[dict[str, Any]] = Field(default_factory=list)


class LocalizeBody(BaseModel):
    locales: list[str] = Field(default_factory=lambda: ["en"])
    fallback: str = "en"
    localized_glossary: list[dict[str, Any]] = Field(default_factory=list)
    region_examples: dict[str, str] = Field(default_factory=dict)


class PublishBody(BaseModel):
    approved: bool = False


class ReviewBody(BaseModel):
    workspace_id: str = "default"
    reviewer_email: str = ""
    reviewer_name: str = "Reviewer"
    summary: str = ""


class VersionBody(BaseModel):
    version: str = Field(min_length=1)


@router.get("")
async def list_domain_packs() -> dict[str, Any]:
    from keprix.backend.domain_packs.filesystem import list_filesystem_packs

    packs = get_domain_pack_store().list_packs()
    payload = [pack.to_dict() for pack in packs]
    known = {str(p.get("domain_name") or "").lower() for p in payload}
    for fs_pack in list_filesystem_packs():
        name = str(fs_pack.get("domain_name") or "").lower()
        if name and name not in known:
            payload.append(fs_pack)
            known.add(name)
    return {"packs": payload, "count": len(payload)}


@router.post("")
async def create_domain_pack(body: CreatePackBody) -> dict[str, Any]:
    manifest = create_manifest_from_template(body.domain_name, jurisdictions=body.jurisdictions)
    saved = get_domain_pack_store().save_pack(manifest)
    return {"pack": saved.to_dict()}


@router.get("/{pack_id}")
async def get_domain_pack(pack_id: str) -> dict[str, Any]:
    pack = get_domain_pack_store().get_pack(pack_id)
    if pack is None:
        raise HTTPException(404, "Domain pack not found")
    return {"pack": pack.to_dict()}


@router.put("/{pack_id}")
async def update_domain_pack(pack_id: str, body: UpdatePackBody) -> dict[str, Any]:
    store = get_domain_pack_store()
    pack = store.get_pack(pack_id)
    if pack is None:
        raise HTTPException(404, "Domain pack not found")
    patch = body.model_dump(exclude_none=True)
    if "glossary" in patch:
        pack.glossary = [GlossaryTerm.from_dict(row) for row in patch.pop("glossary")]
    if "sources" in patch:
        pack.sources = [PackSource.from_dict(row) for row in patch.pop("sources")]
    for key, value in patch.items():
        setattr(pack, key, value)
    saved = store.save_pack(pack)
    return {"pack": saved.to_dict()}


@router.post("/{pack_id}/validate")
async def validate_domain_pack(pack_id: str, for_publish: bool = False) -> dict[str, Any]:
    pack = get_domain_pack_store().get_pack(pack_id)
    if pack is None:
        raise HTTPException(404, "Domain pack not found")
    result = validate_pack(pack, for_publish=for_publish)
    get_domain_pack_store().save_pack(pack)
    return result.to_dict()


@router.post("/{pack_id}/ingest")
async def ingest_domain_pack_sources(pack_id: str, body: IngestBody) -> dict[str, Any]:
    store = get_domain_pack_store()
    pack = store.get_pack(pack_id)
    if pack is None:
        raise HTTPException(404, "Domain pack not found")
    pack = ingest_sources(pack, body.sources)
    saved = store.save_pack(pack)
    return {"pack": saved.to_dict()}


@router.post("/{pack_id}/localize")
async def localize_domain_pack(pack_id: str, body: LocalizeBody) -> dict[str, Any]:
    store = get_domain_pack_store()
    pack = store.get_pack(pack_id)
    if pack is None:
        raise HTTPException(404, "Domain pack not found")
    pack = apply_localization(
        pack,
        locales=body.locales,
        fallback=body.fallback,
        localized_glossary=body.localized_glossary,
        region_examples=body.region_examples,
    )
    saved = store.save_pack(pack)
    sync = await sync_glossary_to_localization(saved)
    return {"pack": saved.to_dict(), "localization_sync": sync}


@router.post("/{pack_id}/review-request")
async def request_domain_pack_review(pack_id: str, body: ReviewBody) -> dict[str, Any]:
    store = get_domain_pack_store()
    pack = store.get_pack(pack_id)
    if pack is None:
        raise HTTPException(404, "Domain pack not found")
    req, token = await create_review_request(
        workspace_id=body.workspace_id,
        title=f"Domain pack review: {pack.domain_name}",
        context_message=body.summary or f"Review required for {pack.domain_name} v{pack.version}",
        artifact_type="domain_pack",
        artifact_content=str(pack.to_dict()),
        reviewer_name=body.reviewer_name,
        reviewer_email=body.reviewer_email or "reviewer@example.com",
    )
    pack.review_status = "pending"
    store.save_pack(pack)
    return {"pack": pack.to_dict(), "review": req.to_dict(), "review_token": token}


@router.post("/{pack_id}/publish")
async def publish_domain_pack(pack_id: str, body: PublishBody) -> dict[str, Any]:
    store = get_domain_pack_store()
    pack = store.get_pack(pack_id)
    if pack is None:
        raise HTTPException(404, "Domain pack not found")
    result = publish_to_hub(pack, approved=body.approved)
    if result.get("status") == "error":
        raise HTTPException(422, detail=result)
    store.save_pack(pack)
    return result


@router.post("/{pack_id}/version")
async def bump_domain_pack_version(pack_id: str, body: VersionBody) -> dict[str, Any]:
    store = get_domain_pack_store()
    pack = store.get_pack(pack_id)
    if pack is None:
        raise HTTPException(404, "Domain pack not found")
    pack = bump_version(pack, body.version)
    saved = store.save_pack(pack)
    return {"pack": saved.to_dict()}
