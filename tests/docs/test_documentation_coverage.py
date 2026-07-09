"""Documentation portal and coverage guards."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
CATALOG = ROOT / "frontend" / "src" / "lib" / "docs-catalog.ts"
MKDOCS = ROOT / "mkdocs.yml"


def test_docs_index_exists() -> None:
    assert (DOCS / "index.md").is_file()


def test_mkdocs_lists_workspace_features() -> None:
    text = MKDOCS.read_text(encoding="utf-8")
    for slug in ("features/chat.md", "features/calendar.md", "features/email.md", "opportunity-engine.md"):
        assert slug in text


def test_docs_catalog_covers_major_sections() -> None:
    text = CATALOG.read_text(encoding="utf-8")
    for label in ("Getting started", "Workspace", "Security and admin", "Integrations and reference"):
        assert label in text


def test_new_feature_guides_exist() -> None:
    required = [
        "features/chat.md",
        "features/settings.md",
        "features/calendar.md",
        "features/developer-platform.md",
        "operations/admin-dashboard.md",
        "security/governance.md",
    ]
    for relative in required:
        assert (DOCS / relative).is_file(), relative
