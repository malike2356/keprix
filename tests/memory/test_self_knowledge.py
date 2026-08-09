"""Self-knowledge retrieval honesty for Propreneur product pack (prompt 643)."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_self_doc_paths_include_propreneur_honesty_corpus() -> None:
    from keprix.memory.rag.self_knowledge import _SELF_DOC_PATHS

    required = {
        "docs/self-knowledge/propreneur-product-pack-honesty.md",
        "docs/architecture/propreneur-approvals-idempotency-events.md",
        "docs/architecture/propreneur-connector-trusted-identity.md",
        "docs/architecture/propreneur-e2e-testing.md",
        "docs/troubleshooting/propreneur-sidecar.md",
        "docs/propreneur-sidecar/README.md",
        "domain-packs/propreneur/docs/propreneur-aiva-capability-guidance.md",
    }
    missing = required - set(_SELF_DOC_PATHS)
    assert not missing, f"missing curated self-doc paths: {sorted(missing)}"
    for rel in required:
        assert (ROOT / rel).is_file(), rel


def test_generated_self_knowledge_includes_propreneur_pack() -> None:
    from keprix.self_knowledge.documents import generate_all_documents

    docs = generate_all_documents()
    by_id = {d.source_id: d for d in docs}
    assert "propreneur_product_pack" in by_id
    text = by_id["propreneur_product_pack"].content.lower()
    assert "soft wall" in text
    assert "source of truth" in text
    assert "/settings/sidecars/propreneur" in by_id["propreneur_product_pack"].content
    assert "intentionally_forbidden" in text or "forbidden" in text


def test_curated_docs_answer_retrieval_questions() -> None:
    honesty = (ROOT / "docs/self-knowledge/propreneur-product-pack-honesty.md").read_text(
        encoding="utf-8"
    ).lower()
    guidance = (
        ROOT / "domain-packs/propreneur/docs/propreneur-aiva-capability-guidance.md"
    ).read_text(encoding="utf-8").lower()
    troubleshooting = (ROOT / "docs/troubleshooting/propreneur-sidecar.md").read_text(
        encoding="utf-8"
    ).lower()
    blob = "\n".join([honesty, guidance, troubleshooting])

    assert "can keprix perform propreneur crud" in honesty or "perform propreneur crud" in honesty
    assert "approval" in blob and "soft wall" in blob
    assert "hard delete" in blob
    assert "correlation_id" in blob or "correlation id" in blob
    assert "source of truth" in blob
    assert "/opt/lampp/htdocs/verlox/propreneur" in honesty
    assert "connectivity" in blob and "crud readiness" in blob
    # Stale nested path may appear only as an explicit "not ..." correction.
    assert honesty.count("propreneur/propreneur-v2") <= 1
    if "propreneur/propreneur-v2" in honesty:
        assert "not" in honesty.split("propreneur/propreneur-v2")[0][-40:].lower()


def test_operator_ui_and_readiness_route_exist() -> None:
    page = ROOT / "frontend/src/app/(workspace)/settings/sidecars/propreneur/page.tsx"
    assert page.is_file()
    source = page.read_text(encoding="utf-8")
    assert "/v1/products/propreneur/readiness" in source
    assert "crud_complete" in source

    routes = (ROOT / "src/keprix/product_sidecar/routes.py").read_text(encoding="utf-8")
    assert '"{product_key}/readiness"' in routes or "/readiness" in routes

    nav_py = (ROOT / "src/keprix/ui_contract/navigation.py").read_text(encoding="utf-8")
    nav_ts = (ROOT / "frontend/src/lib/navigation.ts").read_text(encoding="utf-8")
    assert "/settings/sidecars/propreneur" in nav_py
    assert "/settings/sidecars/propreneur" in nav_ts


def test_readiness_builder_exposes_operator_fields() -> None:
    from keprix.product_sidecar.readiness import build_product_readiness

    ready = build_product_readiness("propreneur")
    assert ready["product"] == "propreneur"
    assert "CRUD readiness" in ready["note"] or "crud readiness" in ready["note"].lower()
    assert "operation_counts" in ready
    assert "pending_approvals" in ready
    assert "event_lag" in ready
    assert ready["source_of_truth"].startswith("Propreneur")
    assert ready["actor_and_tenant_binding"]["model_cannot_override_identity"] is True


@pytest.mark.asyncio
async def test_product_readiness_http_route() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from keprix.product_sidecar.routes import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    response = client.get("/v1/products/propreneur/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["product"] == "propreneur"
    assert "operation_counts" in body
    health = client.get("/v1/products/propreneur/health")
    assert health.status_code == 200
    assert "readiness" in health.json()
