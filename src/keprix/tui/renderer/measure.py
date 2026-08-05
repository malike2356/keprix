"""Text measurement helpers for terminal rendering."""

import re
import unicodedata

from keprix.tui.unicode_width import char_width, text_width

ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
RICH_TAG_RE = re.compile(r"\[/?[a-zA-Z][^\]]*]")
ZWJ = "\u200d"


def measure_text(text: str) -> int:
    if not text:
        return 0
    if "\x1b" not in text and "[" not in text and ZWJ not in text and all(ord(char) < 128 for char in text):
        return len(text)
    return sum(cluster_width(cluster) for cluster in iter_grapheme_clusters(text))


def strip_terminal_markup(text: str) -> str:
    return RICH_TAG_RE.sub("", ANSI_RE.sub("", text))


def iter_grapheme_clusters(text: str) -> list[str]:
    cleaned = strip_terminal_markup(text)
    clusters: list[str] = []
    index = 0
    while index < len(cleaned):
        cluster = cleaned[index]
        index += 1
        while index < len(cleaned):
            char = cleaned[index]
            if char == ZWJ and index + 1 < len(cleaned):
                cluster += char + cleaned[index + 1]
                index += 2
                continue
            if unicodedata.category(char) in {"Mn", "Me", "Cf"}:
                cluster += char
                index += 1
                continue
            break
        clusters.append(cluster)
    return clusters


def cluster_width(cluster: str) -> int:
    if ZWJ in cluster:
        return 2
    return max(0, text_width(cluster))


def clamp_text(text: str, max_width: int) -> str:
    if max_width <= 0:
        return ""
    width = 0
    output: list[str] = []
    for char in iter_grapheme_clusters(text):
        next_width = cluster_width(char)
        if width + next_width > max_width:
            break
        output.append(char)
        width += next_width
    return "".join(output)


def fit_terminal_width(text: str, width: int, *, ellipsis: str = "...") -> str:
    if measure_text(text) <= width:
        return strip_terminal_markup(text)
    if width <= measure_text(ellipsis):
        return clamp_text(ellipsis, width)
    return f"{clamp_text(text, width - measure_text(ellipsis))}{ellipsis}"


__all__ = [
    "ANSI_RE",
    "RICH_TAG_RE",
    "clamp_text",
    "cluster_width",
    "fit_terminal_width",
    "iter_grapheme_clusters",
    "measure_text",
    "strip_terminal_markup",
]
