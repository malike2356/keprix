"""Single source of truth for Keprix machine-readable product specification."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SPEC_VERSION = "1.0.0"

# Amounts are minor units (pence) for machine filters; never scrape HTML for price.
_PRICING_TIERS: list[dict[str, Any]] = [
    {
        "id": "community",
        "name": "Community",
        "description": "Free self-hosted Community Edition (BYOK)",
        "amountMinor": 0,
        "amountMajor": 0,
        "currency": "GBP",
        "interval": None,
        "seats": 1,
        "sso": False,
        "apiAccess": False,
        "managedAi": False,
        "stripePriceId": None,
        "features": [
            "self_hosted",
            "byok",
            "agent_apps",
            "local_governance",
        ],
    },
    {
        "id": "pro_month",
        "name": "Pro",
        "description": "Hosted Pro for professionals",
        "amountMinor": 4900,
        "amountMajor": 49,
        "currency": "GBP",
        "interval": "month",
        "seats": 1,
        "sso": False,
        "apiAccess": False,
        "managedAi": True,
        "stripePriceId": "price_1Trhnm2WMXleLh8eevN9oBYd",
        "features": [
            "managed_ai_credits",
            "full_governance",
            "agent_apps_pro_templates",
            "scheduled_agent_apps",
        ],
    },
    {
        "id": "pro_year",
        "name": "Pro (annual)",
        "description": "Hosted Pro billed annually",
        "amountMinor": 44900,
        "amountMajor": 449,
        "currency": "GBP",
        "interval": "year",
        "seats": 1,
        "sso": False,
        "apiAccess": False,
        "managedAi": True,
        "stripePriceId": "price_1Trhnl2WMXleLh8e9zAYG7F4",
        "features": [
            "managed_ai_credits",
            "full_governance",
            "agent_apps_pro_templates",
            "scheduled_agent_apps",
        ],
    },
    {
        "id": "team_month",
        "name": "Team",
        "description": "Hosted Team for organizations",
        "amountMinor": 12900,
        "amountMajor": 129,
        "currency": "GBP",
        "interval": "month",
        "seats": 10,
        "sso": False,
        "apiAccess": True,
        "managedAi": True,
        "stripePriceId": "price_1Trhnm2WMXleLh8etXFvF1VN",
        "features": [
            "api_access",
            "managed_ai_credits",
            "agent_apps_webhooks",
            "priority_support",
        ],
    },
    {
        "id": "team_year",
        "name": "Team (annual)",
        "description": "Hosted Team billed annually",
        "amountMinor": 129000,
        "amountMajor": 1290,
        "currency": "GBP",
        "interval": "year",
        "seats": 10,
        "sso": False,
        "apiAccess": True,
        "managedAi": True,
        "stripePriceId": "price_1Trhnm2WMXleLh8eYFIXHNDI",
        "features": [
            "api_access",
            "managed_ai_credits",
            "agent_apps_webhooks",
            "priority_support",
        ],
    },
]

_ADDONS: list[dict[str, Any]] = [
    {
        "id": "sso",
        "name": "Single Sign-On",
        "description": "SAML/OIDC enterprise SSO (Team)",
        "amountMinor": 9900,
        "amountMajor": 99,
        "currency": "GBP",
        "interval": "month",
        "appliesTo": ["team"],
        "stripePriceId": "price_1Trhno2WMXleLh8eoiU1Gasw",
        "capability": "sso",
    },
    {
        "id": "extra_seats",
        "name": "Extra Seats",
        "amountMinor": 1500,
        "amountMajor": 15,
        "currency": "GBP",
        "interval": "month",
        "appliesTo": ["team"],
        "stripePriceId": "price_1Trhnn2WMXleLh8epAMAXzFJ",
        "capability": "extra_seats",
    },
]


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
            "Self-hosted AI agent OS with tools, playbooks, memory, governance, "
            "and optional hosted plans. Community Edition is free (BYOK); hosted "
            "Pro starts at 49 GBP/month."
        ),
        "url": "https://keprixai.com",
        "appUrl": "https://app.keprixai.com",
        "repositoryUrl": "https://github.com/malike2356/keprix",
        "license": "MIT",
        "pricingModel": "freemium_hosted_plus_credits",
        "pricingModels": ["self_hosted_free", "subscription", "managed_ai_credits"],
        "pricingTiers": list(_PRICING_TIERS),
        "addons": list(_ADDONS),
        "currency": "GBP",
        "trialDays": 14,
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
            "hostedTargetPercent": 99.5,
            "contractual": False,
            "notes": (
                "Hosted target for app.keprixai.com; Community self-host uptime "
                "is operator-owned."
            ),
        },
        "dataExportFormats": [
            "json",
            "jsonl",
            "csv",
            "markdown",
            "zip_workspace_export",
        ],
        "apiDocsUrl": "https://app.keprixai.com/openapi.json",
        "humanDocsUrl": "https://keprixai.com/guide/",
        "pricingUrl": "https://keprixai.com/pricing",
        "installManifestUrl": "https://keprixai.com/install.json",
        "productSchemaUrl": "https://app.keprixai.com/api/product-schema.json",
        "supportedRegions": ["GB", "EU", "US", "global_self_host"],
        "deploymentOptions": ["docker_compose", "bare_metal_pip", "hosted_saas"],
        "sso": {
            "available": True,
            "includedInPlans": [],
            "addonId": "sso",
            "addonAmountMajor": 99,
            "addonCurrency": "GBP",
            "protocols": ["SAML", "OIDC"],
        },
        "contact": {
            "supportEmail": "billing@verlox.uk",
            "company": "Verlox Ltd",
            "companyAddress": "Portsmouth, UK",
        },
    }
