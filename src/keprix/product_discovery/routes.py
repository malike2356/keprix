"""Public machine-readable discovery endpoints (no auth)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from keprix.product_discovery.filter import evaluate_buy_decision
from keprix.product_discovery.install_manifest import build_install_manifest
from keprix.product_discovery.llms_txt import build_ai_txt, build_llms_txt
from keprix.product_discovery.llm_auditor import (
    audit_llm_discovery,
    generate_llm_visibility_report,
)
from keprix.product_discovery.schema_markup import (
    build_json_ld_graph,
    validate_schema_markup,
)
from keprix.product_discovery.spec import build_product_spec

router = APIRouter(tags=["product-discovery"])


@router.get("/api/product-schema.json")
async def product_schema_json() -> JSONResponse:
    return JSONResponse(build_json_ld_graph())


@router.get("/api/discovery/product-spec")
@router.get("/productSpec.json")
async def product_spec() -> JSONResponse:
    return JSONResponse(build_product_spec())


@router.get("/api/discovery/install")
@router.get("/install.json")
async def install_manifest() -> JSONResponse:
    return JSONResponse(build_install_manifest())


@router.get("/api/discovery/llms.txt")
@router.get("/llms.txt")
async def llms_txt() -> PlainTextResponse:
    return PlainTextResponse(build_llms_txt(), media_type="text/plain; charset=utf-8")


@router.get("/api/discovery/ai.txt")
@router.get("/ai.txt")
async def ai_txt() -> PlainTextResponse:
    return PlainTextResponse(build_ai_txt(), media_type="text/plain; charset=utf-8")


@router.get("/.well-known/keprix.json")
async def well_known_keprix() -> JSONResponse:
    spec = build_product_spec()
    return JSONResponse(
        {
            "name": spec["name"],
            "version": spec["version"],
            "productSpec": "https://keprixai.com/productSpec.json",
            "install": spec["installManifestUrl"],
            "openapi": spec["apiDocsUrl"],
            "schema": spec["productSchemaUrl"],
            "llmsTxt": "https://keprixai.com/llms.txt",
            "app": spec["appUrl"],
            "home": spec["url"],
        }
    )


@router.get("/api/discovery/schema-validation")
async def schema_validation() -> dict[str, Any]:
    errors = validate_schema_markup()
    return {"ok": not errors, "errors": errors}


@router.post("/api/discovery/evaluate")
async def evaluate(criteria: dict[str, Any]) -> dict[str, Any]:
    return evaluate_buy_decision(criteria)


@router.post("/api/discovery/llm-audit")
async def llm_audit(
    dry_run: bool = Query(default=True),
    category: str = Query(default="self-hosted AI agent OS"),
) -> dict[str, Any]:
    """Run LLM visibility probes. Defaults to dry_run to avoid spend."""
    audit = audit_llm_discovery(category=category, dry_run=dry_run)
    return generate_llm_visibility_report(audit)
