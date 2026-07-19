"""Tests for PreambleLoader."""

from __future__ import annotations

from pathlib import Path

from keprix.skills.preamble_loader import PreambleLoader

PERSONAS = Path(__file__).resolve().parents[1].parent / "src" / "keprix" / "personas"


def test_loads_all_skill_files():
    loader = PreambleLoader(str(PERSONAS))
    assert len(loader._personas) >= 11


def test_tier_1_under_500_tokens():
    loader = PreambleLoader(str(PERSONAS))
    ctx = loader.tier_1_context()
    assert ctx
    assert len(ctx) // 4 < 500


def test_tier_3_cso_returns_warden():
    loader = PreambleLoader(str(PERSONAS))
    ctx = loader.tier_3_context("/cso")
    assert len(ctx) > 500
    assert "security" in ctx.lower() or "vulnerability" in ctx.lower()


def test_unknown_phase_and_command_empty():
    loader = PreambleLoader(str(PERSONAS))
    assert loader.tier_2_context("not-a-phase") == ""
    assert loader.tier_3_context("/unknown-command-xyz") == ""
