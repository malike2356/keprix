"""Obsidian markdown parsing tests."""

from __future__ import annotations

from keprix.research_workspace.obsidian.frontmatter import dump_frontmatter, parse_frontmatter
from keprix.research_workspace.obsidian.markdown import analyze_markdown, wikilink
from keprix.research_workspace.obsidian.tags import tags_from_note


def test_frontmatter_roundtrip():
    meta = {"title": "Paper", "tags": ["research"], "keprix_trace_id": "t-1"}
    body = "# Paper\n\nContent."
    text = dump_frontmatter(meta, body)
    parsed_meta, parsed_body = parse_frontmatter(text)
    assert parsed_meta["title"] == "Paper"
    assert parsed_meta["keprix_trace_id"] == "t-1"
    assert "# Paper" in parsed_body


def test_wikilinks_tags_tasks_headings():
    body = (
        "# Intro\n\n"
        "Link to [[source-1]] and [web](https://example.org).\n\n"
        "#task/item #research\n\n"
        "- [ ] Open question\n"
        "- [x] Done item\n"
    )
    note = analyze_markdown(body)
    assert "source-1" in note.wikilinks
    assert note.markdown_links == [("web", "https://example.org")]
    assert "research" in note.tags
    assert note.tasks == [(False, "Open question"), (True, "Done item")]
    assert note.headings[0] == (1, "Intro")


def test_tags_merge_frontmatter_and_body():
    meta = {"tags": ["literature", "keprix"]}
    body = "Tagged #field-note here."
    tags = tags_from_note(meta, body)
    assert "literature" in tags
    assert "field-note" in tags


def test_wikilink_helper():
    assert wikilink("index") == "[[index]]"
    assert wikilink("index", "Home") == "[[index|Home]]"
