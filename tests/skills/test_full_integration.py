"""Full integration test: all 11 personas + 5 infrastructure modules."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.memory.gbrain import GBrain
from keprix.skills import KeprixSkills

PERSONAS = Path(__file__).resolve().parents[1].parent / "src" / "keprix" / "personas"


@pytest.fixture
def ks():
    return KeprixSkills(personas_dir=str(PERSONAS), gbrain_db=":memory:")


@pytest.mark.parametrize(
    "user_input,expected_persona,expected_command",
    [
        # NEXUS; THINK + SHIP
        ("/office-hours", "nexus", "/office-hours"),
        ("brainstorm this feature", "nexus", "/office-hours"),
        ("is this worth building", "nexus", "/office-hours"),
        ("/autoplan", "nexus", "/autoplan"),
        ("ship it", "nexus", "/ship"),
        ("deploy to production", "nexus", "/land-and-deploy"),
        ("/canary", "nexus", "/canary"),
        # COMPASS; PLAN
        ("/plan-ceo-review", "compass", "/plan-ceo-review"),
        ("should we pivot", "compass", "/plan-ceo-review"),
        ("kill this feature", "compass", "/plan-ceo-review"),
        ("narrow the scope", "compass", "/plan-ceo-review"),
        # FORGE; REVIEW + BUILD
        ("/review", "forge", "/review"),
        ("review my pull request", "forge", "/review"),
        ("code review this", "forge", "/review"),
        ("engineering feasibility check", "forge", "/plan-eng-review"),
        ("devex check", "forge", "/devex-review"),
        # BEACON; BUILD
        ("/design-consultation", "beacon", "/design-consultation"),
        ("design shotgun this", "beacon", "/design-shotgun"),
        ("generate html for landing page", "beacon", "/design-html"),
        ("/design-review", "beacon", "/design-review"),
        # CODEX; BUILD
        ("/codex", "codex", "/codex"),
        ("legal review please", "codex", "/codex"),
        ("check licenses", "codex", "/codex"),
        ("gdpr compliance check", "codex", "/codex"),
        # WARDEN; SECURITY
        ("/cso", "warden", "/cso"),
        ("security audit", "warden", "/cso"),
        ("vulnerability scan", "warden", "/cso"),
        ("/investigate", "warden", "/investigate"),
        ("root cause analysis", "warden", "/investigate"),
        # PRISM; TEST
        ("/qa", "prism", "/qa"),
        ("test this", "prism", "/qa"),
        ("run qa tests", "prism", "/qa"),
        ("/qa-only", "prism", "/qa-only"),
        # SAGE; REFLECT
        ("/retro", "sage", "/retro"),
        ("what did we learn this week", "sage", "/retro"),
        ("/benchmark", "sage", "/benchmark"),
        ("performance test", "sage", "/benchmark"),
        ("/learn", "sage", "/learn"),
        # ECHO; REFLECT
        ("/document-release", "echo", "/document-release"),
        ("generate release notes", "echo", "/document-release"),
        ("/document-generate", "echo", "/document-generate"),
        ("generate docs", "echo", "/document-generate"),
        # EMBER; OPS
        ("/connect-chrome", "ember", "/connect-chrome"),
        ("/setup-deploy", "ember", "/setup-deploy"),
        # SCOUT; CONTINUOUS
        ("/careful", "scout", "/careful"),
        ("/freeze", "scout", "/freeze"),
        ("/guard", "scout", "/guard"),
        ("/unfreeze", "scout", "/unfreeze"),
    ],
)
def test_trigger_routing(ks, user_input, expected_persona, expected_command):
    result = ks.triggers.route(user_input)
    assert result is not None, f"No route for: {user_input}"
    persona, command = result
    assert persona == expected_persona, f"Expected {expected_persona}, got {persona} for '{user_input}'"
    assert command == expected_command, f"Expected {expected_command}, got {command} for '{user_input}'"


def test_unknown_input_returns_none(ks):
    assert ks.triggers.route("random gibberish xyz123") is None
    assert ks.triggers.route("") is None
    assert ks.triggers.route("hello how are you") is None


def test_scout_freeze(ks):
    ks.handle_input("/freeze")
    assert ks.scout.should_block_write() is True
    assert ks.scout.frozen is True


def test_scout_unfreeze(ks):
    ks.scout.freeze()
    ks.handle_input("/unfreeze")
    assert ks.scout.should_block_write() is False
    assert ks.scout.caution_level == "normal"


def test_scout_guard(ks):
    ks.handle_input("/guard")
    assert ks.scout.caution_level == "guard"
    assert ks.scout.should_confirm("read_file") is True


def test_scout_careful(ks):
    ks.handle_input("/careful")
    assert ks.scout.should_confirm("write_file") is True
    assert ks.scout.should_confirm("read_file") is False


def test_sprint_phases_advance(ks):
    assert ks.sprint.current_phase.value == "think"
    ks.sprint.advance()
    assert ks.sprint.current_phase.value == "plan"
    ks.sprint.advance()
    assert ks.sprint.current_phase.value == "build"
    ks.sprint.advance()
    assert ks.sprint.current_phase.value == "review"


def test_sprint_phases_full_cycle(ks):
    # think → plan → build → review → test → ship → reflect (6 advances)
    for _ in range(6):
        ks.sprint.advance()
    assert ks.sprint.current_phase.value == "reflect"
    ks.sprint.advance()  # wraps back
    assert ks.sprint.current_phase.value == "think"


def test_available_personas_by_phase(ks):
    assert set(ks.sprint.available_personas()) >= {"nexus", "compass"}

    ks.sprint.set_phase("ship")
    assert ks.sprint.available_personas() == ["nexus"]

    ks.sprint.set_phase("build")
    assert set(ks.sprint.available_personas()) >= {"forge", "codex", "beacon", "ember"}


def test_tier_1_loads_all_personas(ks):
    context = ks.preamble.tier_1_context()
    assert len(context) > 0
    assert "NEXUS" in context or "nexus" in context.lower()
    assert "FORGE" in context or "forge" in context.lower()
    assert "WARDEN" in context or "warden" in context.lower()


def test_tier_3_loads_specific_command(ks):
    context = ks.preamble.tier_3_context("/cso")
    assert len(context) > 500
    assert "security" in context.lower() or "vulnerability" in context.lower()


def test_gbrain_save_and_retrieve(ks):
    gb = GBrain(":memory:")
    gb.save("keprix", "nexus", "decision", "Approved feature X for v0.4")
    results = gb.query("keprix", "nexus", {"type": "decision", "limit": 5})
    assert "Approved feature X" in results


def test_gbrain_search(ks):
    gb = GBrain(":memory:")
    gb.save("keprix", "warden", "incident", "SQL injection found in login form")
    gb.save("keprix", "warden", "incident", "XSS in comment field")
    results = gb.search("keprix", "SQL injection")
    assert len(results) >= 1
    assert "login form" in results[0]["content"]


def test_all_personas_exist(ks):
    expected = {
        "nexus",
        "compass",
        "forge",
        "beacon",
        "codex",
        "warden",
        "prism",
        "sage",
        "echo",
        "ember",
        "scout",
    }
    loaded = set(ks.preamble._personas.keys())
    missing = expected - loaded
    assert not missing, f"Missing personas: {missing}"


def test_all_commands_listed(ks):
    commands = ks.triggers.list_commands()
    command_names = {c["command"] for c in commands}
    required = {
        "/office-hours",
        "/autoplan",
        "/ship",
        "/land-and-deploy",
        "/canary",
        "/plan-ceo-review",
        "/review",
        "/plan-eng-review",
        "/devex-review",
        "/design-consultation",
        "/design-shotgun",
        "/design-html",
        "/design-review",
        "/plan-design-review",
        "/codex",
        "/cso",
        "/investigate",
        "/qa",
        "/qa-only",
        "/retro",
        "/benchmark",
        "/learn",
        "/document-release",
        "/document-generate",
        "/connect-chrome",
        "/setup-browser-cookies",
        "/setup-deploy",
        "/careful",
        "/freeze",
        "/guard",
        "/unfreeze",
    }
    missing = required - command_names
    assert not missing, f"Missing commands in list_commands(): {missing}"
