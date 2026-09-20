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
        "installCommand": "curl -fsSL https://keprixai.com/install.sh | bash",
        "alternateInstallCommands": [
            {
                "id": "dashboard_persist",
                "command": "keprix dashboard install",
                "docs": "https://keprixai.com/guide/getting-started/dashboard/",
            },
            {
                "id": "docker_compose",
                "command": (
                    "docker compose -f docker/docker-compose.yml up -d --build"
                ),
                "docs": "https://keprixai.com/guide/getting-started/quickstart/",
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
                "id": "cli_version",
                "command": "keprix --version",
            },
            {
                "id": "dashboard_ui",
                "command": "curl -fsSI http://127.0.0.1:9120/home",
                "expectHttp": 200,
                "optional": True,
            },
            {
                "id": "compose_health",
                "command": "curl -fsS http://127.0.0.1:3333/api/health",
                "expectHttp": 200,
                "optional": True,
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
            "Reload your shell, then run keprix (offers setup if no provider key)",
            "Optional web UI: keprix dashboard or keprix dashboard install "
            "(http://127.0.0.1:9120/home). There is no hosted workspace at "
            "app.keprixai.com.",
            "Grant AI feature consent under Privacy when KEPRIX_AI_CONSENT_REQUIRED=true",
        ],
    }
