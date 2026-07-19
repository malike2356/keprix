"""Tests for SprintFlow."""

from __future__ import annotations

from keprix.memory.gbrain import GBrain
from keprix.skills.sprint_flow import SprintFlow, SprintPhase


def test_starts_in_think():
    sf = SprintFlow(GBrain(":memory:"))
    assert sf.current_phase == SprintPhase.THINK


def test_advance_walks_phases():
    sf = SprintFlow(GBrain(":memory:"))
    assert sf.advance() == SprintPhase.PLAN
    assert sf.advance() == SprintPhase.BUILD
    assert sf.advance() == SprintPhase.REVIEW
    assert sf.advance() == SprintPhase.TEST
    assert sf.advance() == SprintPhase.SHIP
    assert sf.advance() == SprintPhase.REFLECT
    assert sf.advance() == SprintPhase.THINK


def test_available_personas_build():
    sf = SprintFlow(GBrain(":memory:"))
    sf.set_phase(SprintPhase.BUILD)
    assert sf.available_personas() == ["forge", "codex", "beacon", "ember"]


def test_available_personas_ship():
    sf = SprintFlow(GBrain(":memory:"))
    sf.set_phase(SprintPhase.SHIP)
    assert sf.available_personas() == ["nexus"]


def test_set_phase_skip():
    sf = SprintFlow(GBrain(":memory:"))
    sf.set_phase(SprintPhase.SHIP)
    assert sf.current_phase == SprintPhase.SHIP


def test_checkpoint_restore():
    gb = GBrain(":memory:")
    sf = SprintFlow(gb)
    sf.set_phase(SprintPhase.TEST)
    sf.checkpoint()
    sf2 = SprintFlow(gb)
    assert sf2.current_phase == SprintPhase.TEST
