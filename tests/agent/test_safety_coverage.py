"""Safety layer coverage tests (prompt 289)."""

from __future__ import annotations

from agent.layers.safety import SAFETY_LAYER


def test_safety_layer_covers_all_categories():
    required = (
        "Child safety",
        "Weapons",
        "Malicious code",
        "Medical",
        "Self-harm",
        "Creative content",
        "Refusal tone",
    )
    for label in required:
        assert label in SAFETY_LAYER
