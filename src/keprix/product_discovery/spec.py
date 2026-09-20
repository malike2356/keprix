"""Single source of truth for Keprix machine-readable product specification."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SPEC_VERSION = "1.1.0"

# Amounts are minor units (pence) for machine filters; never scrape HTML for price.
# Public catalog is Community Edition only. Operators may enable their own Stripe
# catalog on a self-hosted instance; Verlox does not sell hosted Pro/Team.
_PRICING_TIERS: list[dict[str, Any]] = [
    {
        "id": "community",
        "name": "Community",
        "description": "Free self-hosted Community Edition (BYOK)",
        "amountMinor": 0,
        "amountMajor": 0,
        "currency": "GBP",
        "interval": None,
        "seats": None,
        "sso": True,
        "apiAccess": True,
        "managedAi": False,
        "stripePriceId": None,
        "features": [
            "self_hosted",
            "byok",
            "agent_apps",
            "local_governance",
            "local_web_dashboard",
        ],
    },
]

_ADDONS: list[dict[str, Any]] = []


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_product_spec(*, last_updated: str | None = None) -> dict[str, Any]:
    """Canonical productSpec.json payload for AI agent discovery."""
    return {
        "version": SPEC_VERSION,
        "lastUpdated": last_updated or _utcnow(),
        "name": "Keprix",
        "legalName": "Keprix by Verlox Ltd",
        "category": "AI agent operating system",
        "categories": [
            "ai-agent-os",
            "self-hosted-ai",
            "developer-tools",
            "automation",
        ],
        "description": (
            "Self-hosted AI agent OS with tools, playbooks, memory, and "
            "governance. Community Edition is free (BYOK). Run the workspace "
            "on your machine with keprix dashboard; keprixai.com is marketing "
            "and docs only."
        ),
        "url": "https://keprixai.com",
        "appUrl": "https://keprixai.com/docs",
        "repositoryUrl": "https://github.com/malike2356/keprix",
        "license": "MIT",
        "pricingModel": "self_hosted_open_source",
        "pricingModels": ["self_hosted_free", "operator_stripe_optional"],
        "pricingTiers": list(_PRICING_TIERS),
        "addons": list(_ADDONS),
        "currency": "GBP",
        "trialDays": 0,
        "integrations": [
            {"id": "openai", "name": "OpenAI", "type": "llm"},
            {"id": "anthropic", "name": "Anthropic", "type": "llm"},
            {"id": "deepseek", "name": "DeepSeek", "type": "llm"},
            {"id": "gemini", "name": "Google Gemini", "type": "llm"},
            {"id": "mcp", "name": "Model Context Protocol", "type": "protocol"},
            {"id": "slack", "name": "Slack", "type": "channel"},
            {"id": "discord", "name": "Discord", "type": "channel"},
            {"id": "telegram", "name": "Telegram", "type": "channel"},
            {"id": "github", "name": "GitHub", "type": "scm"},
            {"id": "google_workspace", "name": "Google Workspace", "type": "productivity"},
            {"id": "stripe", "name": "Stripe", "type": "billing"},
            {"id": "companies_house", "name": "Companies House", "type": "data"},
        ],
        "features": [
            "agent_runtime",
            "tool_calling",
            "playbooks",
            "memory_rag",
            "mcp_host",
            "cron",
            "self_hosted",
            "docker_compose",
            "governance_audit",
            "credential_vault",
            "domain_packs",
            "customer_concierge",
            "ai_transparency_sgi",
        ],
        "securityCertifications": [
            # Honest: no SOC 2 attestation claimed in-repo as of this spec version.
        ],
        "securityControls": [
            "credential_vault",
            "audit_log",
            "review_gateway",
            "tenant_isolation",
            "eu_ai_act_sgi_disclosure",
            "append_only_generation_log",
        ],
        "compliance": [
            "GDPR",
            "UK_GDPR",
            "EU_AI_Act_transparency_SGI",
            "MIT_license_self_host",
        ],
        "uptimeSLA": {
            "hostedTargetPercent": None,
            "contractual": False,
            "notes": (
                "No hosted workspace. Uptime is operator-owned on the machine "
                "where you run keprix dashboard or Docker Compose."
            ),
        },
        "dataExportFormats": [
            "json",
            "jsonl",
            "csv",
            "markdown",
            "zip_workspace_export",
        ],
        "apiDocsUrl": "https://keprixai.com/guide/reference/api/",
        "humanDocsUrl": "https://keprixai.com/guide/",
        "pricingUrl": "https://keprixai.com/pricing",
        "installManifestUrl": "https://keprixai.com/install.json",
        "productSchemaUrl": "https://keprixai.com/product-schema.json",
        "supportedRegions": ["GB", "EU", "US", "global_self_host"],
        "deploymentOptions": [
            "curl_cli",
            "keprix_dashboard",
            "docker_compose",
            "desktop_rc",
        ],
        "sso": {
            "available": True,
            "includedInPlans": ["community"],
            "addonId": None,
            "addonAmountMajor": 0,
            "addonCurrency": "GBP",
            "protocols": ["SAML", "OIDC"],
        },
        "contact": {
            "supportEmail": "billing@verlox.uk",
            "company": "Verlox Ltd",
            "companyAddress": "Portsmouth, UK",
        },
    }
