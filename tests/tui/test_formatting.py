"""TUI markdown formatting tests."""

from __future__ import annotations

from rich.markdown import Markdown
from rich.text import Text

from keprix.tui.formatting import agent_markdown, plain_text


def test_plain_text_is_not_markup() -> None:
    rendered = plain_text("Use [bold] and **stars** literally")
    assert isinstance(rendered, Text)
    assert "[bold]" in str(rendered)


def test_agent_markdown_parses_bold() -> None:
    rendered = agent_markdown("**Chat** and `code`")
    assert isinstance(rendered, Markdown)
