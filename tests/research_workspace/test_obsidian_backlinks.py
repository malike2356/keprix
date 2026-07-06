"""Obsidian backlink tests."""

from __future__ import annotations

from pathlib import Path

from keprix.research_workspace.obsidian.attachments import preserve_attachment_links
from keprix.research_workspace.obsidian.backlinks import backlinks_for, build_backlink_index


def test_backlink_index(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    (root / "source.md").write_text("# Source\n\nSupports [[claim-a]].\n", encoding="utf-8")
    (root / "claim-a.md").write_text("# Claim\n\nFrom [[source]].\n", encoding="utf-8")
    index = build_backlink_index(list(root.glob("*.md")))
    assert "source" in index["claim-a"]
    assert backlinks_for("claim-a", index) == ["source"]


def test_preserve_attachment_embeds():
    original = "Body text.\n\n![[chart.png]]\n"
    updated = "New body text.\n"
    merged = preserve_attachment_links(original, updated)
    assert "![[chart.png]]" in merged
    assert "New body text." in merged
