"""Documentation URL and portal guards."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE_INDEX = ROOT / "frontend" / "public" / "guide" / "index.html"
DOCS_URL_TS = ROOT / "frontend" / "src" / "lib" / "docs-url.ts"


def test_default_docs_base_is_same_origin_guide() -> None:
    text = DOCS_URL_TS.read_text(encoding="utf-8")
    assert 'DEFAULT_DOCS_BASE = "/guide"' in text
    assert "github.io" not in text


def test_built_guide_index_exists_after_mkdocs_build() -> None:
    assert GUIDE_INDEX.is_file(), "Run bash scripts/build-docs.sh to generate frontend/public/guide/"
