"""Slash command argument parsing."""

from __future__ import annotations

from dataclasses import dataclass, field
import shlex


@dataclass(frozen=True)
class ParsedSlashArgs:
    command: str
    positional: list[str] = field(default_factory=list)
    flags: dict[str, str | bool] = field(default_factory=dict)


def parse_slash_args(text: str) -> ParsedSlashArgs:
    parts = shlex.split(text)
    if not parts:
        return ParsedSlashArgs(command="")
    command = parts[0]
    positional: list[str] = []
    flags: dict[str, str | bool] = {}
    index = 1
    while index < len(parts):
        part = parts[index]
        if part.startswith("--"):
            key = part[2:]
            if "=" in key:
                name, value = key.split("=", 1)
                flags[name] = value
            elif index + 1 < len(parts) and not parts[index + 1].startswith("-"):
                flags[key] = parts[index + 1]
                index += 1
            else:
                flags[key] = True
        else:
            positional.append(part)
        index += 1
    return ParsedSlashArgs(command=command, positional=positional, flags=flags)
