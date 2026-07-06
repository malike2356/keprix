"""PSPP output parsing."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._current_table: list[list[str]] = []
        self._current_row: list[str] = []
        self._cell_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._in_table = True
            self._current_table = []
        elif self._in_table and tag == "tr":
            self._in_row = True
            self._current_row = []
        elif self._in_row and tag in {"td", "th"}:
            self._in_cell = True
            self._cell_chunks = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "table" and self._in_table:
            self.tables.append(self._current_table)
            self._in_table = False
        elif tag == "tr" and self._in_row:
            self._current_table.append(self._current_row)
            self._in_row = False
        elif tag in {"td", "th"} and self._in_cell:
            self._current_row.append("".join(self._cell_chunks).strip())
            self._in_cell = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_chunks.append(data)


def parse_text_tables(text: str) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    blocks = re.split(r"\n{2,}", text.strip())
    for block in blocks:
        lines = [line.rstrip() for line in block.splitlines() if line.strip()]
        if len(lines) < 2:
            continue
        if all("  " in line or "\t" in line for line in lines[1:]):
            tables.append({"title": lines[0], "rows": [re.split(r"\s{2,}|\t", line.strip()) for line in lines[1:]]})
    return tables


def parse_output_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8", errors="replace")
    if suffix in {".html", ".htm"}:
        parser = _TableParser()
        parser.feed(text)
        return {"format": "html", "tables": parser.tables, "raw_path": str(path)}
    return {"format": suffix.lstrip(".") or "txt", "tables": parse_text_tables(text), "raw_path": str(path)}
