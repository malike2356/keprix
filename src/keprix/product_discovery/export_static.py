"""Export discovery artifacts into frontend/public for marketing host static serve."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from keprix.product_discovery.install_manifest import build_install_manifest
from keprix.product_discovery.llms_txt import build_ai_txt, build_llms_txt
from keprix.product_discovery.schema_markup import build_json_ld_graph
from keprix.product_discovery.spec import build_product_spec


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def export_static(public_dir: Path | None = None) -> list[Path]:
    root = _repo_root()
    public = public_dir or (root / "frontend" / "public")
    public.mkdir(parents=True, exist_ok=True)
    well_known = public / ".well-known"
    well_known.mkdir(parents=True, exist_ok=True)

    # Freeze lastUpdated for reproducible static exports in CI.
    spec = build_product_spec(last_updated="2026-08-10T00:00:00Z")
    written: list[Path] = []

    def write_json(path: Path, payload: object) -> None:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        written.append(path)

    write_json(public / "productSpec.json", spec)
    write_json(public / "install.json", build_install_manifest())
    write_json(public / "product-schema.json", build_json_ld_graph(spec))
    write_json(well_known / "keprix.json", {
        "name": spec["name"],
        "version": spec["version"],
        "productSpec": "/productSpec.json",
        "install": "/install.json",
        "openapi": "https://app.keprixai.com/openapi.json",
        "schema": "https://app.keprixai.com/api/product-schema.json",
        "llmsTxt": "/llms.txt",
        "app": spec["appUrl"],
        "home": spec["url"],
    })

    llms_path = public / "llms.txt"
    llms_path.write_text(build_llms_txt(), encoding="utf-8")
    written.append(llms_path)

    ai_path = public / "ai.txt"
    ai_path.write_text(build_ai_txt(), encoding="utf-8")
    written.append(ai_path)

    robots = public / "robots.txt"
    robots.write_text(
        "\n".join(
            [
                "User-agent: *",
                "Allow: /",
                "Allow: /productSpec.json",
                "Allow: /install.json",
                "Allow: /llms.txt",
                "Allow: /ai.txt",
                "Allow: /.well-known/",
                "Sitemap: https://keprixai.com/sitemap.xml",
                "",
            ]
        ),
        encoding="utf-8",
    )
    written.append(robots)

    sitemap = public / "sitemap.xml"
    sitemap.write_text(
        "\n".join(
            [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
                "  <url><loc>https://keprixai.com/</loc></url>",
                "  <url><loc>https://keprixai.com/pricing</loc></url>",
                "  <url><loc>https://keprixai.com/features</loc></url>",
                "  <url><loc>https://keprixai.com/docs</loc></url>",
                "  <url><loc>https://keprixai.com/guide/</loc></url>",
                "  <url><loc>https://keprixai.com/productSpec.json</loc></url>",
                "  <url><loc>https://keprixai.com/install.json</loc></url>",
                "  <url><loc>https://keprixai.com/llms.txt</loc></url>",
                "</urlset>",
                "",
            ]
        ),
        encoding="utf-8",
    )
    written.append(sitemap)
    return written


def main(argv: list[str] | None = None) -> int:
    paths = export_static()
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
