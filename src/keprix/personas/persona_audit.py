"""Persona comparison against leak patterns (Prompt 290)."""

from __future__ import annotations

from typing import TypedDict


class PersonaAuditEntry(TypedDict):
    patterns_adopted: list[str]
    missing: list[str]
    confidence: str


PERSONA_AUDIT: dict[str, PersonaAuditEntry] = {
    "nexus": {
        "patterns_adopted": ["Cursor IDE task-first routing", "delegation over execution"],
        "missing": ["Multi-agent handoff telemetry from Claude Code"],
        "confidence": "high",
    },
    "forge": {
        "patterns_adopted": ["Cursor IDE task-first", "ponytail ladder", "read-before-write"],
        "missing": ["Silent tool mode from Cursor"],
        "confidence": "high",
    },
    "warden": {
        "patterns_adopted": ["Fable 5 refusal framework", "Fable 5 safety tiers"],
        "missing": ["Threat modelling templates from Microsoft Copilot"],
        "confidence": "medium",
    },
    "sage": {
        "patterns_adopted": ["Claude Code plan-before-acting", "Fable 5 citation discipline"],
        "missing": ["Search depth escalation from Perplexity"],
        "confidence": "high",
    },
    "beacon": {
        "patterns_adopted": ["Notion AI clean prose output", "workspace brand context"],
        "missing": ["Inline collaborative editing from Notion AI"],
        "confidence": "medium",
    },
    "prism": {
        "patterns_adopted": ["Cursor IDE data-first recommendations", "measurable outcomes"],
        "missing": ["Automated rank tracking dashboards"],
        "confidence": "medium",
    },
    "compass": {
        "patterns_adopted": ["Claude Code plan-before-acting", "structured option framing"],
        "missing": ["Monte Carlo scenario simulation"],
        "confidence": "high",
    },
    "ember": {
        "patterns_adopted": ["Notion AI workspace awareness", "confidentiality defaults"],
        "missing": ["Fable 5 voice tone for spoken check-ins"],
        "confidence": "medium",
    },
    "codex": {
        "patterns_adopted": ["Cursor IDE task-first", "read-before-analyse", "minimal prose"],
        "missing": ["Automated clause library sync from Cursor codebase index"],
        "confidence": "high",
    },
    "echo": {
        "patterns_adopted": ["Notion AI workspace awareness", "Fable 5 voice tone"],
        "missing": ["Multi-channel routing from Fable 5"],
        "confidence": "medium",
    },
}


def get_persona_audit(persona_name: str) -> PersonaAuditEntry | None:
    return PERSONA_AUDIT.get(persona_name.lower())


def list_audited_personas() -> list[str]:
    return sorted(PERSONA_AUDIT)
