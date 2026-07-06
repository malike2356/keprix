"""Rich renderables for TUI message content."""

from __future__ import annotations

from rich.markdown import Markdown
from rich.text import Text


def plain_text(content: str) -> Text:
    """User or system text without Rich markup or markdown parsing."""
    return Text(content)


def agent_markdown(content: str) -> Markdown | Text:
    """Render assistant markdown; fall back to plain text on parse errors."""
    text = content.strip()
    if not text:
        return Text("")
    try:
        return Markdown(
            text,
            code_theme="monokai",
            hyperlinks=True,
        )
    except Exception:
        return Text(text)
