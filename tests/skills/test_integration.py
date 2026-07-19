"""Integration tests for KeprixSkills orchestrator."""

from __future__ import annotations

from pathlib import Path

from keprix.skills import KeprixSkills
from keprix.skills.sprint_flow import SprintPhase

PERSONAS = Path(__file__).resolve().parents[1].parent / "src" / "keprix" / "personas"


def test_freeze_via_handle_input():
    ks = KeprixSkills(str(PERSONAS), ":memory:")
    result = ks.handle_input("/freeze")
    assert result["frozen"] is True
    assert ks.scout.should_block_write() is True


def test_ship_it_in_ship_phase():
    ks = KeprixSkills(str(PERSONAS), ":memory:")
    ks.sprint.set_phase(SprintPhase.SHIP)
    result = ks.handle_input("ship it")
    assert result["persona"] == "nexus"
    assert result["command"] == "/ship"
    assert result.get("context")
    assert result["mode"] == "persona"


def test_ship_it_in_think_phase_errors():
    ks = KeprixSkills(str(PERSONAS), ":memory:")
    assert ks.sprint.current_phase == SprintPhase.THINK
    result = ks.handle_input("ship it")
    assert result["mode"] == "error"
    assert "Not in SHIP phase" in result["error"]


def test_audit_routes_warden():
    ks = KeprixSkills(str(PERSONAS), ":memory:")
    result = ks.handle_input("audit my code")
    assert result["persona"] == "warden"
    assert result["command"] == "/cso"


def test_design_review_routes_beacon():
    ks = KeprixSkills(str(PERSONAS), ":memory:")
    result = ks.handle_input("does this look good")
    assert result["persona"] == "beacon"
    assert result["command"] == "/design-review"


def test_retro_routes_sage():
    ks = KeprixSkills(str(PERSONAS), ":memory:")
    result = ks.handle_input("what did we learn this week")
    assert result["persona"] == "sage"
    assert result["command"] == "/retro"


def test_unknown_default_mode():
    ks = KeprixSkills(str(PERSONAS), ":memory:")
    result = ks.handle_input("random gibberish xyz")
    assert result["mode"] == "default"
    assert result["persona"] is None
