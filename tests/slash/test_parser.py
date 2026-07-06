"""Tests for slash command parsing."""

from __future__ import annotations

import pytest

from keprix.slash.parser import parse_slash


@pytest.fixture
def known():
    return ["help", "status", "memory.search", "memory.save", "tool.run", "research"]


def test_quoted_args_parse(known):
    parsed = parse_slash('/memory save "Client prefers Monday calls"', known)
    assert parsed.command == "memory.save"
    assert parsed.args == ["Client prefers Monday calls"]


def test_json_args_parse(known):
    parsed = parse_slash("""/tool run search --json '{"query":"acme"}'""", known)
    assert parsed.command == "tool.run"
    assert parsed.args == ["search"]
    assert parsed.json_args == {"query": "acme"}


def test_flags_parse(known):
    parsed = parse_slash('/research "market map" --depth deep --model local', known)
    assert parsed.command == "research"
    assert parsed.args == ["market map"]
    assert parsed.flags["depth"] == "deep"
    assert parsed.flags["model"] == "local"


def test_unknown_command_suggestions(known):
    parsed = parse_slash("/statuz", known)
    assert parsed.unknown is True
    assert "status" in parsed.suggestions
