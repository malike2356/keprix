"""Workflow variable context tests."""

from __future__ import annotations

from keprix.playbook.variable_context import build_initial_state, validate_variable_refs


def test_build_initial_state_defaults_and_overrides() -> None:
    variables = [
        {"name": "client_email", "type": "string", "default": ""},
        {"name": "min_score", "type": "number", "default": 65},
        {"name": "enabled", "type": "boolean", "default": False},
    ]

    state = build_initial_state(variables, {"client_email": "a@example.com", "enabled": "true"})

    assert state == {"client_email": "a@example.com", "min_score": 65.0, "enabled": True}


def test_validate_variable_refs_warns_for_missing() -> None:
    warnings = validate_variable_refs(
        {
            "variables": [{"name": "known", "type": "string"}],
            "steps": [{"prompt": "Use {{ state.known }} and {{ state.missing }}"}],
        }
    )

    assert warnings == ["state.missing is referenced but not declared in variables"]
