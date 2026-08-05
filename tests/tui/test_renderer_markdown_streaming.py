from __future__ import annotations

from keprix.tui.renderer.code_blocks import detect_partial_code_block, extract_code_blocks, render_code_block
from keprix.tui.renderer.markdown import StreamingMarkdownRenderer, render_streaming_markdown


def test_partial_code_block_is_preserved_during_stream() -> None:
    text = "Before\n\n```python\nprint(1)"
    partial = detect_partial_code_block(text)
    assert partial is not None
    assert partial.language == "python"
    rendered = render_streaming_markdown(text)
    assert "[code:python (streaming)]" in rendered.rendered
    assert rendered.partial_code_language == "python"


def test_closed_code_block_and_links_render_without_crash() -> None:
    text = "See https://example.com\n\n```ts\nconst x = 1\n```"
    blocks = extract_code_blocks(text)
    assert blocks[0].language == "ts"
    assert "[code:ts]" in render_code_block(blocks[0])
    rendered = render_streaming_markdown(text)
    assert rendered.links == ("https://example.com",)


def test_streaming_renderer_preserves_partial_output_on_interrupt() -> None:
    renderer = StreamingMarkdownRenderer()
    result = renderer.update("hello\n\n```py\nx = 1")
    assert result.unstable
    assert renderer.interrupt() == result.rendered
