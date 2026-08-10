"""schema.org JSON-LD builders for SoftwareApplication, Product, and WebAPI."""

from __future__ import annotations

from typing import Any

from keprix.product_discovery.spec import build_product_spec


def _offers(spec: dict[str, Any]) -> list[dict[str, Any]]:
    offers: list[dict[str, Any]] = []
    for tier in spec.get("pricingTiers") or []:
        offer: dict[str, Any] = {
            "@type": "Offer",
            "name": tier.get("name"),
            "price": tier.get("amountMajor"),
            "priceCurrency": tier.get("currency") or "GBP",
            "url": spec.get("pricingUrl"),
            "availability": "https://schema.org/InStock",
            "category": tier.get("id"),
        }
        if tier.get("interval"):
            offer["billingDuration"] = f"P1{str(tier['interval'])[0].upper()}"
            offer["priceSpecification"] = {
                "@type": "UnitPriceSpecification",
                "price": tier.get("amountMajor"),
                "priceCurrency": tier.get("currency") or "GBP",
                "billingDuration": offer["billingDuration"],
                "unitText": tier.get("interval"),
            }
        offers.append(offer)
    return offers


def build_software_application_ld(spec: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = spec or build_product_spec()
    return {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "@id": f"{spec['url']}#software",
        "name": spec["name"],
        "applicationCategory": "DeveloperApplication",
        "applicationSubCategory": spec.get("category"),
        "operatingSystem": "Linux, macOS, Windows (Docker)",
        "description": spec["description"],
        "url": spec["url"],
        "downloadUrl": spec.get("repositoryUrl"),
        "installUrl": spec.get("installManifestUrl"),
        "softwareVersion": spec.get("version"),
        "license": "https://opensource.org/licenses/MIT",
        "offers": _offers(spec),
        "featureList": ", ".join(spec.get("features") or []),
        "provider": {
            "@type": "Organization",
            "name": (spec.get("contact") or {}).get("company") or "Verlox Ltd",
            "url": "https://verlox.uk",
            "email": (spec.get("contact") or {}).get("supportEmail"),
        },
        "isAccessibleForFree": True,
    }


def build_product_ld(spec: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = spec or build_product_spec()
    return {
        "@context": "https://schema.org",
        "@type": "Product",
        "@id": f"{spec['url']}#product",
        "name": spec["name"],
        "description": spec["description"],
        "brand": {
            "@type": "Brand",
            "name": "Keprix",
        },
        "category": spec.get("category"),
        "url": spec["url"],
        "offers": _offers(spec),
    }


def build_web_api_ld(spec: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = spec or build_product_spec()
    return {
        "@context": "https://schema.org",
        "@type": "WebAPI",
        "@id": f"{spec['appUrl']}#webapi",
        "name": "Keprix HTTP API",
        "description": "OpenAPI-described Keprix agent OS HTTP API",
        "documentation": spec.get("apiDocsUrl"),
        "url": spec.get("apiDocsUrl"),
        "provider": {
            "@type": "Organization",
            "name": "Verlox Ltd",
            "url": "https://verlox.uk",
        },
    }


def build_json_ld_graph(spec: dict[str, Any] | None = None) -> dict[str, Any]:
    """Combined @graph suitable for <script type=\"application/ld+json\">."""
    spec = spec or build_product_spec()
    software = build_software_application_ld(spec)
    product = build_product_ld(spec)
    webapi = build_web_api_ld(spec)
    # Strip per-node @context when nesting in @graph
    for node in (software, product, webapi):
        node.pop("@context", None)
    return {
        "@context": "https://schema.org",
        "@graph": [software, product, webapi],
    }


def validate_schema_markup(graph: dict[str, Any] | None = None) -> list[str]:
    """Lightweight schema.org structural checks (zero errors expected)."""
    graph = graph or build_json_ld_graph()
    errors: list[str] = []
    if graph.get("@context") != "https://schema.org":
        errors.append("missing @context https://schema.org")
    nodes = graph.get("@graph") or []
    if not nodes:
        errors.append("empty @graph")
    types = {n.get("@type") for n in nodes}
    for required in ("SoftwareApplication", "Product", "WebAPI"):
        if required not in types:
            errors.append(f"missing @type {required}")
    for node in nodes:
        if node.get("@type") == "SoftwareApplication":
            if not node.get("name"):
                errors.append("SoftwareApplication.name required")
            offers = node.get("offers") or []
            if not offers:
                errors.append("SoftwareApplication.offers required")
            for offer in offers:
                if offer.get("price") is None:
                    errors.append("Offer.price must be numeric")
                if not offer.get("priceCurrency"):
                    errors.append("Offer.priceCurrency required")
    return errors
