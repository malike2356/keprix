"""Document parsing adapters."""

from __future__ import annotations

import io
import json
import os
import zipfile
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from keprix.memory.rag.indexer import (
    parse_csv,
    parse_email,
    parse_html,
    parse_markdown,
    parse_pdf,
    parse_plaintext,
)


class ParseError(ValueError):
    pass


def _ocr_available() -> bool:
    return os.environ.get("KEPRIX_OCR_ENABLED", "false").lower() == "true"


def parse_json(content: str) -> str:
    payload = json.loads(content)
    return json.dumps(payload, indent=2)


def parse_docx(content: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            xml = archive.read("word/document.xml")
        root = ET.fromstring(xml)
        texts = [node.text for node in root.iter() if node.tag.endswith("}t") and node.text]
        return " ".join(texts).strip()
    except Exception as exc:
        raise ParseError("DOCX parsing failed") from exc


def parse_image_ocr(content: bytes) -> str:
    if not _ocr_available():
        raise ImportError("OCR is optional; set KEPRIX_OCR_ENABLED=true and install pytesseract")
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise ImportError("OCR requires pytesseract and Pillow") from exc
    image = Image.open(io.BytesIO(content))
    return pytesseract.image_to_string(image).strip()


def parse_document(*, filename: str, content: bytes | str) -> dict[str, Any]:
    suffix = Path(filename).suffix.lower()
    raw = content if isinstance(content, (bytes, bytearray)) else content.encode("utf-8")
    text_content = content if isinstance(content, str) else None

    if suffix in {".txt", ".text"}:
        parsed = parse_plaintext(text_content or raw.decode("utf-8", errors="ignore"))
        source_type = "plaintext"
    elif suffix == ".md":
        parsed = parse_markdown(text_content or raw.decode("utf-8", errors="ignore"))
        source_type = "markdown"
    elif suffix in {".html", ".htm"}:
        parsed = parse_html(text_content or raw.decode("utf-8", errors="ignore"))
        source_type = "html"
    elif suffix == ".csv":
        parsed = parse_csv(text_content or raw.decode("utf-8", errors="ignore"))
        source_type = "csv"
    elif suffix == ".json":
        parsed = parse_json(text_content or raw.decode("utf-8", errors="ignore"))
        source_type = "json"
    elif suffix == ".pdf":
        parsed = parse_pdf(raw)
        source_type = "pdf"
    elif suffix == ".docx":
        parsed = parse_docx(raw)
        source_type = "docx"
    elif suffix in {".eml", ".email"}:
        parsed = parse_email(raw)
        source_type = "email"
    elif suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        parsed = parse_image_ocr(raw)
        source_type = "image_ocr"
    else:
        parsed = parse_plaintext(text_content or raw.decode("utf-8", errors="ignore"))
        source_type = "plaintext"

    if not parsed.strip():
        raise ParseError(f"No text extracted from {filename}")
    return {"filename": filename, "source_type": source_type, "text": parsed}
