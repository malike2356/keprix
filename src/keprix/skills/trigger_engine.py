"""Natural language to slash-command routing for gstack personas."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

# Command-specific phrases (integration + prompt acceptance). Longer phrases win.
COMMAND_PHRASES: dict[str, list[str]] = {
    "/office-hours": [
        "brainstorm this feature",
        "brainstorm this",
        "brainstorm",
        "is this worth building",
        "worth building",
        "office hours",
        "product review",
        "product interrogation",
    ],
    "/autoplan": ["autoplan", "auto plan", "autonomous planning"],
    "/ship": ["ship it", "merge and ship", "ship this", "ship now"],
    "/land-and-deploy": [
        "deploy to production",
        "land and deploy",
        "deploy",
        "production deploy",
    ],
    "/canary": ["canary", "gradual rollout", "canary rollout"],
    "/plan-ceo-review": [
        "should we pivot",
        "kill this feature",
        "narrow the scope",
        "narrow scope",
        "ceo review",
        "plan ceo",
        "expand scope",
        "pivot",
        "kill this",
    ],
    "/review": [
        "review my pull request",
        "code review this",
        "code review",
        "review my pr",
        "pull request review",
        "pr review",
    ],
    "/plan-eng-review": [
        "engineering feasibility check",
        "engineering feasibility",
        "eng review",
        "feasibility check",
    ],
    "/devex-review": ["devex check", "devex review", "developer experience"],
    "/design-consultation": ["design consultation", "design brainstorm"],
    "/design-shotgun": [
        "design shotgun this",
        "design shotgun",
        "shotgun this",
        "rapid design",
    ],
    "/design-html": [
        "generate html for landing page",
        "generate html",
        "design html",
        "html for landing",
    ],
    "/design-review": [
        "does this look good",
        "design review",
        "looks good",
        "ui review",
    ],
    "/plan-design-review": ["plan design review", "design planning"],
    "/codex": [
        "legal review please",
        "legal review",
        "check licenses",
        "gdpr compliance check",
        "gdpr",
        "license check",
        "compliance check",
    ],
    "/cso": [
        "security audit",
        "vulnerability scan",
        "audit my code",
        "pentest",
        "threat model",
        "is this secure",
        "security review",
    ],
    "/investigate": [
        "root cause analysis",
        "investigate",
        "root cause",
        "debug this",
    ],
    "/qa": [
        "run qa tests",
        "test this",
        "run tests",
        "check for bugs",
        "quality assurance",
        "qa tests",
    ],
    "/qa-only": ["qa-only please", "qa only", "qa-only", "report only qa"],
    "/retro": [
        "what did we learn this week",
        "what did we learn",
        "retrospective",
        "weekly review",
        "retro",
    ],
    "/benchmark": ["performance test", "benchmark", "performance benchmark"],
    "/learn": ["learn from memory", "recall context", "learn"],
    "/document-release": [
        "generate the release notes",
        "generate release notes",
        "release notes",
        "changelog",
    ],
    "/document-generate": ["generate docs", "generate documentation", "write docs"],
    "/connect-chrome": ["connect chrome", "chrome connection", "browser setup"],
    "/setup-browser-cookies": [
        "setup browser cookies",
        "browser cookies",
        "browser auth",
        "authenticate browser",
    ],
    "/setup-deploy": ["setup deploy", "configure deploy", "deployment setup"],
    "/careful": ["careful", "raise caution"],
    "/freeze": ["freeze", "lock files", "read only mode"],
    "/guard": ["guard", "maximum safety", "guard mode"],
    "/unfreeze": ["unfreeze", "unlock files", "release locks"],
}

PERSONA_PHASE: dict[str, str] = {
    "nexus": "think",
    "compass": "plan",
    "forge": "review",
    "beacon": "build",
    "codex": "build",
    "warden": "security",
    "prism": "test",
    "sage": "reflect",
    "echo": "reflect",
    "ember": "ops",
    "scout": "continuous",
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


class TriggerEngine:
    """Routes user input to the correct persona and slash command."""

    def __init__(self, personas_dir: str):
        self.personas_dir = Path(personas_dir)
        self._commands: dict[str, dict[str, Any]] = {}
        self._phrase_index: list[tuple[str, str, str]] = []  # phrase, persona, command
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
            persona = persona_dir.name.lower()
            content = skill_file.read_text(encoding="utf-8")
            frontmatter, body = _parse_frontmatter(content)
            commands = re.findall(r"^###\s+(/[a-z0-9-]+)", body, re.MULTILINE | re.IGNORECASE)
            desc = frontmatter.get("description") or ""
            phase = PERSONA_PHASE.get(persona, "continuous")
            triggers = [str(t).lower() for t in (frontmatter.get("triggers") or [])]

            for cmd in commands:
                cmd = cmd.lower()
                self._commands[cmd] = {
                    "command": cmd,
                    "persona": persona,
                    "phase": phase,
                    "description": desc,
                }
                # Exact command token as phrase
                self._phrase_index.append((cmd.lstrip("/").replace("-", " "), persona, cmd))
                for phrase in COMMAND_PHRASES.get(cmd, []):
                    self._phrase_index.append((phrase.lower(), persona, cmd))

            # Frontmatter triggers: map to best command for this persona via keyword overlap
            for trigger in triggers:
                best_cmd = self._best_command_for_trigger(persona, commands, trigger)
                if best_cmd:
                    self._phrase_index.append((trigger.lower(), persona, best_cmd))

        # Prefer longer phrases first
        self._phrase_index.sort(key=lambda x: len(x[0]), reverse=True)

    def _best_command_for_trigger(
        self, persona: str, commands: list[str], trigger: str
    ) -> str | None:
        if not commands:
            return None
        t = trigger.lower()
        best = None
        best_score = -1
        for cmd in commands:
            tokens = set(re.findall(r"[a-z0-9]+", cmd.lstrip("/")))
            score = sum(1 for tok in tokens if tok in t)
            # Prefer phrases from COMMAND_PHRASES that contain this trigger
            for phrase in COMMAND_PHRASES.get(cmd, []):
                if t in phrase or phrase in t:
                    score += 3
            if score > best_score:
                best_score = score
                best = cmd
        if best_score <= 0:
            # Default to first command listed for persona
            return commands[0].lower()
        return best.lower() if best else commands[0].lower()

    def route(self, user_input: str) -> tuple[str, str] | None:
        """Return (persona_name, command) if matched, else None."""
        if user_input is None:
            return None
        text = user_input.strip()
        if not text:
            return None

        # 1. Exact slash-command match (first token)
        first = text.split()[0].lower()
        if first.startswith("/"):
            cmd = first.split(";")[0]
            if cmd in self._commands:
                return (self._commands[cmd]["persona"], cmd)
            # Unknown slash command: no match
            if re.fullmatch(r"/[a-z0-9-]+", cmd):
                return None

        lower = text.lower()

        # 2. Trigger phrase match (case-insensitive, substring); longest first
        for phrase, persona, command in self._phrase_index:
            if phrase and phrase in lower:
                return (persona, command)

        # 3. Keyword scoring across command phrase tokens
        tokens = set(re.findall(r"[a-z0-9]+", lower))
        if not tokens:
            return None
        scores: dict[tuple[str, str], int] = {}
        for phrase, persona, command in self._phrase_index:
            phrase_tokens = set(re.findall(r"[a-z0-9]+", phrase))
            overlap = len(tokens & phrase_tokens)
            if overlap >= 2 or (overlap == 1 and len(phrase_tokens) == 1 and len(phrase) >= 4):
                key = (persona, command)
                scores[key] = max(scores.get(key, 0), overlap * 10 + len(phrase))
        if not scores:
            return None
        best = max(scores.items(), key=lambda kv: kv[1])
        if best[1] < 10:
            return None
        return best[0]

    def list_commands(self) -> list[dict]:
        """Return all available commands with persona, phase, description."""
        out = []
        for cmd, meta in sorted(self._commands.items()):
            out.append(
                {
                    "command": cmd,
                    "persona": meta["persona"],
                    "phase": meta["phase"],
                    "description": meta["description"],
                }
            )
        return out
