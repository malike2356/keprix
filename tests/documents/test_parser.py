"""Document parser tests."""

import json

import pytest

from keprix.documents.parser import ParseError, parse_document, parse_json


def test_parse_markdown_and_json() -> None:
    markdown = parse_document(filename="note.md", content="# Title\n\nBody text")
    assert markdown["source_type"] == "markdown"
    assert "Body text" in markdown["text"]
    payload = parse_json(json.dumps({"key": "value"}))
    assert "value" in payload


def test_parse_csv_file() -> None:
    parsed = parse_document(filename="data.csv", content="name,score\nAda,99\n")
    assert parsed["source_type"] == "csv"
    assert "Ada" in parsed["text"]


def test_parse_empty_pdf_raises() -> None:
    with pytest.raises(ParseError):
        parse_document(filename="empty.pdf", content=b"%PDF-1.4\n")
