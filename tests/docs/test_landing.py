"""Landing page content and style guards."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LANDING = ROOT / "landing" / "index.html"

FORBIDDEN_DASHES = re.compile("[\u2013\u2014]")
COMPARISON_MARKERS = (
    "Multi-tenant SOC",
    "No (use Petraclus)",
    "Contact sales",
)


def test_landing_page_exists() -> None:
    assert LANDING.exists()


def test_landing_has_no_em_or_en_dashes() -> None:
    text = LANDING.read_text(encoding="utf-8")
    assert not FORBIDDEN_DASHES.search(text), "Remove em/en dashes from landing page"


def test_landing_has_feature_comparison_table() -> None:
    text = LANDING.read_text(encoding="utf-8")
    for marker in COMPARISON_MARKERS:
        assert marker in text


def test_landing_links_to_docs_quickstart() -> None:
    text = LANDING.read_text(encoding="utf-8")
    assert "getting-started/quickstart" in text
