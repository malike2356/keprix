"""Agent install manifest (install.json) for one-click environment setup."""

from __future__ import annotations

from typing import Any

from keprix.product_discovery.spec import SPEC_VERSION, build_product_spec


def build_install_manifest() -> dict[str, Any]:
    spec = build_product_spec()
    return {
        "version": SPEC_VERSION,
        "name": "keprix",
        "displayName": "Keprix",
        "description": spec["description"],
        "homepage": spec["url"],
        "repository": spec["repositoryUrl"],
        "license": "MIT",
        "installCommand": (
            "git clone https://github.com/malike2356/keprix.git && "
            "cd keprix && bash scripts/install.sh"
        ),
        "alternateInstallCommands": [
            {
                "id": "docker_compose",
                "command": (
                    "docker compose -f docker/docker-compose.yml up -d --build"
                ),
                "docs": "https://keprixai.com/guide/",
            },
            {
                "id": "pipx_cli",
                "command": "pipx install '.[tui]' --force && keprix --version",
            },
        ],
        "apiKeySetup": {
            "byok": True,
            "envFile": ".env",
            "notes": (
                "Community is BYOK. Set at least one provider key "
                "(OPENAI_API_KEY, ANTHROPIC_API_KEY, DEEPSEEK_API_KEY, or GEMINI_API_KEY)."
            ),
        },
        "requiredEnvVars": [
            {
                "name": "DEEPSEEK_API_KEY",
                "required": False,
                "description": "DeepSeek API key (common default provider)",
            },
            {
                "name": "OPENAI_API_KEY",
                "required": False,
                "description": "OpenAI API key",
            },
            {
                "name": "ANTHROPIC_API_KEY",
                "required": False,
                "description": "Anthropic API key",
            },
            {
                "name": "KEPRIX_HOME",
                "required": False,
                "description": "Override data home (default ~/.keprix)",
            },
        ],
        "postInstallChecks": [
            {
                "id": "health",
                "command": "curl -fsS http://127.0.0.1:3333/api/health",
                "expectHttp": 200,
            },
            {
                "id": "cli_version",
                "command": "keprix --version",
            },
            {
                "id": "product_spec",
                "url": "https://keprixai.com/productSpec.json",
                "expectJsonKeys": ["name", "pricingTiers", "version"],
            },
        ],
        "discovery": {
            "productSpecUrl": "https://keprixai.com/productSpec.json",
            "openapiUrl": spec["apiDocsUrl"],
            "schemaUrl": spec["productSchemaUrl"],
            "llmsTxtUrl": "https://keprixai.com/llms.txt",
        },
        "configureHints": [
            "Copy .env.example to .env and add a provider API key",
            "For hosted SaaS use https://app.keprixai.com instead of local install",
            "Grant AI feature consent under Privacy when KEPRIX_AI_CONSENT_REQUIRED=true",
        ],
    }
