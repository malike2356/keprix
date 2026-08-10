"""Machine-readable product discovery tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.product_discovery.filter import evaluate_buy_decision
from keprix.product_discovery.install_manifest import build_install_manifest
from keprix.product_discovery.llm_auditor import (
    audit_llm_discovery,
    generate_llm_visibility_report,
)
from keprix.product_discovery.schema_markup import (
    build_json_ld_graph,
    validate_schema_markup,
)
from keprix.product_discovery.spec import build_product_spec


def test_product_spec_has_required_fields_and_numeric_pricing():
    spec = build_product_spec(last_updated="2026-08-10T00:00:00Z")
    for key in (
        "name",
        "category",
        "description",
        "pricingModel",
        "pricingTiers",
        "integrations",
        "securityCertifications",
        "uptimeSLA",
        "dataExportFormats",
        "apiDocsUrl",
        "supportedRegions",
        "compliance",
        "lastUpdated",
        "version",
    ):
        assert key in spec
    assert spec["version"]
    assert spec["lastUpdated"]
    assert isinstance(spec["pricingTiers"], list) and spec["pricingTiers"]
    for tier in spec["pricingTiers"]:
        assert isinstance(tier["amountMajor"], (int, float))
        assert isinstance(tier["amountMinor"], int)
        assert tier["currency"] == "GBP"


def test_schema_markup_validates_zero_errors():
    graph = build_json_ld_graph()
    errors = validate_schema_markup(graph)
    assert errors == []
    types = {n["@type"] for n in graph["@graph"]}
    assert {"SoftwareApplication", "Product", "WebAPI"} <= types


def test_install_manifest():
    manifest = build_install_manifest()
    assert "installCommand" in manifest
    assert "apiKeySetup" in manifest
    assert "requiredEnvVars" in manifest
    assert "postInstallChecks" in manifest


def test_agent_buy_decision_from_product_spec():
    # Under 50 GBP/month with GDPR, without requiring SSO: Pro matches.
    decision = evaluate_buy_decision(
        {
            "maxMonthlyAmountMajor": 50,
            "currency": "GBP",
            "requireSso": False,
            "requireCompliance": ["GDPR"],
        }
    )
    assert decision["buy"] is True
    assert decision["recommended"]["tierId"] in {"community", "pro_month"}
    assert any(m["tierId"] == "pro_month" for m in decision["matches"])

    # SSO + under 50: Team+SSO addon is 129+99 = 228, so no buy.
    sso_decision = evaluate_buy_decision(
        {
            "maxMonthlyAmountMajor": 50,
            "currency": "GBP",
            "requireSso": True,
            "requireCompliance": ["GDPR"],
        }
    )
    assert sso_decision["buy"] is False


def test_llm_auditor_with_fakes():
    def chatgpt(_prompt: str) -> str:
        return "1. Autogen\n2. Keprix - self-hosted agent OS\n3. LangChain"

    def claude(_prompt: str) -> str:
        return "Consider CrewAI and OpenDevin."

    def gemini(_prompt: str) -> str:
        return "1) Keprix\n2) Something else"

    audit = audit_llm_discovery(
        providers={"chatgpt": chatgpt, "claude": claude, "gemini": gemini},
        queries=["recommend a self-hosted AI agent OS tool"],
    )
    report = generate_llm_visibility_report(audit)
    assert "chatgpt" in report["mentionedProviders"]
    assert "gemini" in report["mentionedProviders"]
    assert "claude" not in report["mentionedProviders"]
    assert report["suggestions"]


def test_static_export_files_exist():
    public = Path(__file__).resolve().parents[2] / "frontend" / "public"
    for name in (
        "productSpec.json",
        "install.json",
        "llms.txt",
        "ai.txt",
        "robots.txt",
        "sitemap.xml",
        "product-schema.json",
    ):
        path = public / name
        assert path.is_file(), f"missing {path}"
    spec = json.loads((public / "productSpec.json").read_text(encoding="utf-8"))
    assert spec["name"] == "Keprix"
    assert (public / ".well-known" / "keprix.json").is_file()


@pytest.mark.asyncio
async def test_public_discovery_routes():
    from keprix.api.server import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        schema = await client.get("/api/product-schema.json")
        assert schema.status_code == 200
        body = schema.json()
        assert body["@context"] == "https://schema.org"
        assert any(n.get("@type") == "SoftwareApplication" for n in body["@graph"])

        spec = await client.get("/api/discovery/product-spec")
        assert spec.status_code == 200
        assert spec.json()["name"] == "Keprix"

        install = await client.get("/install.json")
        assert install.status_code == 200
        assert "installCommand" in install.json()

        llms = await client.get("/llms.txt")
        assert llms.status_code == 200
        assert "Keprix" in llms.text

        well = await client.get("/.well-known/keprix.json")
        assert well.status_code == 200
        assert well.json()["openapi"].endswith("/openapi.json")

        decision = await client.post(
            "/api/discovery/evaluate",
            json={
                "maxMonthlyAmountMajor": 50,
                "currency": "GBP",
                "requireCompliance": ["GDPR"],
            },
        )
        assert decision.status_code == 200
        assert decision.json()["buy"] is True
