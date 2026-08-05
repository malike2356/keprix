"""Custom voice persona helpers."""

from __future__ import annotations


def render_custom_persona(name: str, instructions: str) -> str:
    return f"You are {name}. {instructions.strip()}"
