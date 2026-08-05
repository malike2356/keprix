"""Code block extraction and rendering for renderer previews."""

from dataclasses import dataclass
import html
import re


CODE_BLOCK_RE = re.compile(r"```(?P<label>[^\n`]*)\n(?P<body>.*?)```", re.DOTALL)


@dataclass(frozen=True)
class CodeBlock:
    language: str
    body: str
    closed: bool = True


def extract_code_blocks(text: str) -> list[CodeBlock]:
    return [CodeBlock(language=match.group("label").strip(), body=match.group("body")) for match in CODE_BLOCK_RE.finditer(text)]


def detect_partial_code_block(text: str) -> CodeBlock | None:
    fence_count = len(re.findall(r"^```", text, flags=re.MULTILINE))
    if fence_count % 2 == 0:
        return None
    opener = re.search(r"```(?P<label>[^\n`]*)\n(?P<body>.*)$", text, flags=re.DOTALL)
    if opener is None:
        return None
    return CodeBlock(language=opener.group("label").strip(), body=opener.group("body"), closed=False)


def render_code_block(block: CodeBlock) -> str:
    label = block.language or "text"
    suffix = "" if block.closed else " (streaming)"
    body = html.unescape(block.body).rstrip("\n")
    return f"[code:{label}{suffix}]\n{body}"


__all__ = ["CodeBlock", "detect_partial_code_block", "extract_code_blocks", "render_code_block"]
