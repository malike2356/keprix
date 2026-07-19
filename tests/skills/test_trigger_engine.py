"""Tests for TriggerEngine."""

from __future__ import annotations

from pathlib import Path

from keprix.skills.trigger_engine import TriggerEngine

PERSONAS = Path(__file__).resolve().parents[1].parent / "src" / "keprix" / "personas"


def test_exact_slash_cso():
    engine = TriggerEngine(str(PERSONAS))
    assert engine.route("/cso") == ("warden", "/cso")


def test_security_audit():
    engine = TriggerEngine(str(PERSONAS))
    assert engine.route("security audit now") == ("warden", "/cso")


def test_ship_it():
    engine = TriggerEngine(str(PERSONAS))
    assert engine.route("ship it") == ("nexus", "/ship")


def test_worth_building():
    engine = TriggerEngine(str(PERSONAS))
    assert engine.route("is this worth building") == ("nexus", "/office-hours")


def test_review_pr():
    engine = TriggerEngine(str(PERSONAS))
    assert engine.route("review my pull request") == ("forge", "/review")


def test_release_notes():
    engine = TriggerEngine(str(PERSONAS))
    assert engine.route("generate the release notes") == ("echo", "/document-release")


def test_gibberish_none():
    engine = TriggerEngine(str(PERSONAS))
    assert engine.route("random gibberish xyz") is None


def test_list_commands_has_23_plus():
    engine = TriggerEngine(str(PERSONAS))
    commands = engine.list_commands()
    assert len(commands) >= 23
    names = {c["command"] for c in commands}
    assert "/cso" in names
    assert "/ship" in names
    assert "/freeze" in names
    assert "/setup-deploy" in names
