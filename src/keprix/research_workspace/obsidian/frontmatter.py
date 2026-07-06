"""YAML frontmatter parsing for Obsidian notes."""

from __future__ import annotations

import json
import re
from typing import Any

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw = match.group(1)
    body = text[match.end() :]
    meta = _parse_yaml_block(raw)
    return meta, body


def dump_frontmatter(meta: dict[str, Any], body: str) -> str:
    if not meta:
        return body.lstrip("\n")
    lines = ["---"]
    for key, value in meta.items():
        lines.append(f"{key}: {_yaml_value(value)}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + body.lstrip("\n")


def _yaml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    if value is None:
        return "null"
    text = str(value)
    if any(char in text for char in ':"{}[],#'):
        return json.dumps(text)
    return text


def _parse_yaml_block(raw: str) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        meta[key] = _parse_scalar(value)
    return meta


def _parse_scalar(value: str) -> Any:
    if not value:
        return ""
    if value in {"true", "false"}:
        return value == "true"
    if value == "null":
        return None
    if value.startswith("[") or value.startswith("{"):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value
