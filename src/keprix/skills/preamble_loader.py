"""Tiered context loading from persona SKILL.md files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

# Approximate tokens: ~4 chars per token
_CHARS_PER_TOKEN = 4

PHASE_PERSONAS: dict[str, list[str]] = {
    "think": ["nexus", "compass"],
    "plan": ["nexus", "compass", "forge", "beacon"],
    "build": ["forge", "codex", "beacon", "ember"],
    "review": ["forge", "warden", "beacon"],
    "test": ["prism", "sage", "forge"],
    "ship": ["nexus"],
    "reflect": ["sage", "echo"],
    "ops": ["ember"],
    "security": ["warden"],
    "continuous": ["scout", "warden", "ember"],
}

COMMAND_PERSONA: dict[str, str] = {
    "/office-hours": "nexus",
    "/autoplan": "nexus",
    "/ship": "nexus",
    "/land-and-deploy": "nexus",
    "/canary": "nexus",
    "/plan-ceo-review": "compass",
    "/review": "forge",
    "/plan-eng-review": "forge",
    "/devex-review": "forge",
    "/design-consultation": "beacon",
    "/design-shotgun": "beacon",
    "/design-html": "beacon",
    "/design-review": "beacon",
    "/plan-design-review": "beacon",
    "/codex": "codex",
    "/cso": "warden",
    "/investigate": "warden",
    "/qa": "prism",
    "/qa-only": "prism",
    "/browse": "prism",
    "/retro": "sage",
    "/benchmark": "sage",
    "/learn": "sage",
    "/setup-gbrain": "sage",
    "/document-release": "echo",
    "/document-generate": "echo",
    "/connect-chrome": "ember",
    "/setup-browser-cookies": "ember",
    "/setup-deploy": "ember",
    "/careful": "scout",
    "/freeze": "scout",
    "/guard": "scout",
    "/unfreeze": "scout",
}


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", content, re.DOTALL)
    if not match:
        return {}, content
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        data = {}
    return data, match.group(2).strip()


def _identity_summary(persona: str, frontmatter: dict[str, Any], body: str) -> str:
    desc = frontmatter.get("description") or ""
    role = ""
    role_match = re.search(r"\*\*Role:\*\*\s*(.+)", body)
    if role_match:
        role = role_match.group(1).strip()
    name = frontmatter.get("name") or persona
    parts = [f"**{persona.upper()}** ({name})"]
    if role:
        parts.append(role)
    elif desc:
        parts.append(desc)
    return " ".join(parts)


class PreambleLoader:
    """Loads persona SKILL.md files by tier.

    Tier 1: always loaded (persona identity, core methodology)
    Tier 2: loaded when user enters the persona's sprint phase
    Tier 3: loaded only when a specific slash command is invoked
    """

    def __init__(self, personas_dir: str):
        self.personas_dir = Path(personas_dir)
        self._personas: dict[str, dict[str, Any]] = {}
        self._by_tier: dict[int, list[str]] = {1: [], 2: [], 3: []}
        self._load_all()

    def _load_all(self) -> None:
        if not self.personas_dir.is_dir():
            return
        for persona_dir in sorted(self.personas_dir.iterdir()):
            if not persona_dir.is_dir():
                continue
            skill_file = persona_dir / "SKILL.md"
            if not skill_file.exists():
                continue
            content = skill_file.read_text(encoding="utf-8")
            frontmatter, body = _parse_frontmatter(content)
            name = persona_dir.name.lower()
            tier = int(frontmatter.get("preamble-tier", 2) or 2)
            if tier not in (1, 2, 3):
                tier = 2
            commands = re.findall(r"^###\s+(/[a-z0-9-]+)", body, re.MULTILINE | re.IGNORECASE)
            self._personas[name] = {
                "name": name,
                "frontmatter": frontmatter,
                "body": body,
                "tier": tier,
                "commands": commands,
                "triggers": [str(t).lower() for t in (frontmatter.get("triggers") or [])],
                "identity": _identity_summary(name, frontmatter, body),
            }
            self._by_tier.setdefault(tier, []).append(name)

    def tier_1_context(self) -> str:
        """Return concatenated tier-1 identity summaries (under ~500 tokens)."""
        parts: list[str] = []
        budget_chars = 500 * _CHARS_PER_TOKEN
        used = 0
        for name in self._by_tier.get(1, []):
            persona = self._personas[name]
            line = persona["identity"]
            if used + len(line) + 1 > budget_chars and parts:
                break
            parts.append(line)
            used += len(line) + 1
        # Also include short identity for any loaded persona marked tier 1 in frontmatter
        # already handled via _by_tier
        return "\n".join(parts)

    def tier_2_context(self, active_phase: str) -> str:
        """Return tier-2 sections for personas assigned to active_phase."""
        phase = (active_phase or "").lower().strip()
        if not phase:
            return ""
        names = PHASE_PERSONAS.get(phase, [])
        if not names:
            return ""
        parts: list[str] = []
        for name in names:
            persona = self._personas.get(name)
            if not persona:
                continue
            # Prefer identity + operating principles excerpt for phase context
            body = persona["body"]
            principles = ""
            m = re.search(
                r"##\s+Operating Principles\s*\n(.*?)(?=\n##\s|\Z)",
                body,
                re.DOTALL | re.IGNORECASE,
            )
            if m:
                principles = m.group(1).strip()[:800]
            parts.append(
                f"### {name.upper()}\n{persona['identity']}\n\n{principles}".strip()
            )
        return "\n\n".join(parts)

    def tier_3_context(self, command: str) -> str:
        """Return full SKILL.md body for the persona that owns this command."""
        if not command:
            return ""
        cmd = command.strip()
        if not cmd.startswith("/"):
            cmd = f"/{cmd}"
        cmd = cmd.lower()
        owner = COMMAND_PERSONA.get(cmd)
        if owner and owner in self._personas:
            return self._personas[owner]["body"]
        # Fallback: scan bodies for the command heading
        for persona in self._personas.values():
            if cmd in persona["commands"] or re.search(
                rf"^###\s+{re.escape(cmd)}\b", persona["body"], re.MULTILINE | re.IGNORECASE
            ):
                return persona["body"]
        return ""
