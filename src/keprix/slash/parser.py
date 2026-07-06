"""Slash command parser with quoted args, flags, and JSON payloads."""

from __future__ import annotations

import difflib
import json
import re
import shlex
from typing import Iterable

from keprix.slash.schemas import ParsedSlash

_BOT_SUFFIX = re.compile(r"^(.+?)@[\w_]+$")


def _strip_bot_suffix(token: str) -> str:
    match = _BOT_SUFFIX.match(token)
    return match.group(1) if match else token


def _split_flags(tokens: list[str]) -> tuple[list[str], dict[str, str], dict[str, Any] | None]:
    positional: list[str] = []
    flags: dict[str, str] = {}
    json_args: dict[str, Any] | None = None
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        if token == "--json":
            if idx + 1 >= len(tokens):
                raise ValueError("Missing JSON payload after --json")
            json_args = json.loads(tokens[idx + 1])
            idx += 2
            continue
        if token.startswith("--"):
            key = token[2:]
            if idx + 1 < len(tokens) and not tokens[idx + 1].startswith("--"):
                flags[key] = tokens[idx + 1]
                idx += 2
            else:
                flags[key] = "true"
                idx += 1
            continue
        positional.append(token)
        idx += 1
    return positional, flags, json_args


def _candidate_commands(known: Iterable[str]) -> list[str]:
    return sorted({name.lower() for name in known})


def _resolve_command(tokens: list[str], known: Iterable[str]) -> tuple[str, list[str]]:
    known_list = _candidate_commands(known)
    if not tokens:
        return "", []
    first = _strip_bot_suffix(tokens[0].lstrip("/").lower())
    rest = tokens[1:]
    for width in (3, 2, 1):
        if len(tokens) < width:
            continue
        parts = [_strip_bot_suffix(tokens[i].lstrip("/").lower()) for i in range(width)]
        candidate = ".".join(parts)
        if candidate in known_list:
            return candidate, tokens[width:]
    if first in known_list:
        return first, rest
    return first, rest


def parse_slash(raw_text: str, known_commands: Iterable[str]) -> ParsedSlash:
    text = raw_text.strip()
    if not text.startswith("/"):
        raise ValueError("Slash commands must start with /")
    body = text[1:].strip()
    if not body:
        return ParsedSlash(command="", args=[], flags={}, json_args=None, raw_text=text, unknown=True)

    try:
        tokens = shlex.split(body)
    except ValueError as exc:
        raise ValueError(f"Invalid slash command quoting: {exc}") from exc

    positional, flags, json_args = _split_flags(tokens)
    command, args = _resolve_command(positional, known_commands)
    known = _candidate_commands(known_commands)
    unknown = command not in known
    suggestions: list[str] = []
    if unknown and command:
        suggestions = difflib.get_close_matches(command, known, n=3, cutoff=0.5)

    return ParsedSlash(
        command=command,
        args=args,
        flags=flags,
        json_args=json_args,
        raw_text=text,
        unknown=unknown,
        suggestions=suggestions,
    )
