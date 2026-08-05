"""Streaming-safe markdown rendering."""

import re
from dataclasses import dataclass

from keprix.tui.renderer.code_blocks import detect_partial_code_block, extract_code_blocks, render_code_block
from keprix.tui.streaming_markdown import StreamingMarkdownState, find_stable_boundary

LINK_RE = re.compile(r"https?://[^\s)]+")


@dataclass(frozen=True)
class MarkdownRenderResult:
    stable: str
    unstable: str
    rendered: str
    links: tuple[str, ...]
    partial_code_language: str = ""


class StreamingMarkdownRenderer:
    def __init__(self) -> None:
        self.state = StreamingMarkdownState()
        self.last_rendered = ""

    def update(self, text: str) -> MarkdownRenderResult:
        stable, unstable = self.state.update(text)
        result = render_streaming_markdown(text, stable=stable, unstable=unstable)
        self.last_rendered = result.rendered
        return result

    def interrupt(self) -> str:
        return self.last_rendered


def render_streaming_markdown(text: str, *, stable: str | None = None, unstable: str | None = None) -> MarkdownRenderResult:
    if stable is None or unstable is None:
        state = StreamingMarkdownState()
        stable, unstable = state.update(text)
    partial = detect_partial_code_block(text)
    rendered = text
    for block in extract_code_blocks(text):
        rendered = rendered.replace(f"```{block.language}\n{block.body}```", render_code_block(block))
    if partial is not None:
        rendered = rendered[: rendered.rfind("```")] + render_code_block(partial)
    links = tuple(match.group(0) for match in LINK_RE.finditer(text))
    return MarkdownRenderResult(
        stable=stable,
        unstable=unstable,
        rendered=rendered,
        links=links,
        partial_code_language=partial.language if partial is not None else "",
    )


__all__ = [
    "MarkdownRenderResult",
    "StreamingMarkdownRenderer",
    "StreamingMarkdownState",
    "find_stable_boundary",
    "render_streaming_markdown",
]
