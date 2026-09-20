"""Generate llms.txt / ai.txt discovery documents."""

from __future__ import annotations

from keprix.product_discovery.spec import build_product_spec


def build_llms_txt() -> str:
    spec = build_product_spec()
    lines = [
        "# Keprix",
        "",
        f"> {spec['description']}",
        "",
        "## Product",
        "",
        f"- Home: {spec['url']}",
        f"- Docs catalog: {spec['appUrl']}",
        f"- Local workspace: http://127.0.0.1:9120/home after `keprix dashboard`",
        f"- Docs: {spec['humanDocsUrl']}",
        f"- Pricing: {spec['pricingUrl']}",
        f"- OpenAPI: {spec['apiDocsUrl']}",
        f"- Product spec (JSON): {spec['url'].rstrip('/')}/productSpec.json",
        f"- Install manifest: {spec['installManifestUrl']}",
        f"- Schema graph: {spec['productSchemaUrl']}",
        "",
        "## Pricing (machine-readable)",
        "",
    ]
    for tier in spec["pricingTiers"]:
        interval = tier.get("interval") or "one-time/free"
        lines.append(
            f"- {tier['name']}: {tier['amountMajor']} {tier['currency']} / {interval} "
            f"(sso={tier.get('sso')}, api={tier.get('apiAccess')})"
        )
    lines.extend(
        [
            "",
            "## Compliance",
            "",
            *[f"- {c}" for c in spec.get("compliance") or []],
            "",
            "## Install",
            "",
            "- Prefer install.json for agent-driven setup",
            "- curl -fsSL https://keprixai.com/install.sh | bash",
            "- Local UI: keprix dashboard install (http://127.0.0.1:9120/home)",
            "- Optional Docker: docker compose -f docker/docker-compose.yml up -d --build",
            "",
        ]
    )
    return "\n".join(lines)


def build_ai_txt() -> str:
    return "\n".join(
        [
            "# ai.txt for Keprix",
            "contact: billing@verlox.uk",
            "product-spec: https://keprixai.com/productSpec.json",
            "install: https://keprixai.com/install.json",
            "openapi: https://keprixai.com/guide/reference/api/",
            "llms: https://keprixai.com/llms.txt",
            "schema: https://keprixai.com/product-schema.json",
            "",
        ]
    )
