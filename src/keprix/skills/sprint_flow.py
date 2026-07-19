"""Guided 7-phase sprint workflow: Think → Plan → Build → Review → Test → Ship → Reflect."""

from __future__ import annotations

from enum import Enum
from typing import Any

from keprix.memory.gbrain import GBrain


class SprintPhase(Enum):
    THINK = "think"
    PLAN = "plan"
    BUILD = "build"
    REVIEW = "review"
    TEST = "test"
    SHIP = "ship"
    REFLECT = "reflect"


PHASE_ORDER = [
    SprintPhase.THINK,
    SprintPhase.PLAN,
    SprintPhase.BUILD,
    SprintPhase.REVIEW,
    SprintPhase.TEST,
    SprintPhase.SHIP,
    SprintPhase.REFLECT,
]

PHASE_PERSONAS: dict[SprintPhase, list[str]] = {
    SprintPhase.THINK: ["nexus", "compass"],
    SprintPhase.PLAN: ["nexus", "compass", "forge", "beacon"],
    SprintPhase.BUILD: ["forge", "codex", "beacon", "ember"],
    SprintPhase.REVIEW: ["forge", "warden", "beacon"],
    SprintPhase.TEST: ["prism", "sage", "forge"],
    SprintPhase.SHIP: ["nexus"],
    SprintPhase.REFLECT: ["sage", "echo"],
}

PHASE_COMMANDS: dict[SprintPhase, list[str]] = {
    SprintPhase.THINK: ["/office-hours", "/plan-ceo-review"],
    SprintPhase.PLAN: [
        "/autoplan",
        "/plan-eng-review",
        "/plan-design-review",
        "/plan-ceo-review",
        "/devex-review",
    ],
    SprintPhase.BUILD: [
        "/codex",
        "/design-consultation",
        "/design-shotgun",
        "/design-html",
        "/setup-deploy",
        "/connect-chrome",
    ],
    SprintPhase.REVIEW: ["/review", "/cso", "/design-review", "/investigate"],
    SprintPhase.TEST: ["/qa", "/qa-only", "/benchmark"],
    SprintPhase.SHIP: ["/ship", "/land-and-deploy", "/canary"],
    SprintPhase.REFLECT: ["/retro", "/learn", "/document-release", "/document-generate"],
}

SHIP_COMMANDS = frozenset({"/ship", "/land-and-deploy", "/canary"})

CHECKPOINT_TYPE = "session_summary"
CHECKPOINT_PROJECT = "_sprint"
CHECKPOINT_PERSONA = "nexus"


class SprintFlow:
    def __init__(self, gbrain: GBrain | str | None = None):
        if isinstance(gbrain, GBrain):
            self.gbrain = gbrain
        elif isinstance(gbrain, str):
            self.gbrain = GBrain(gbrain)
        else:
            self.gbrain = GBrain(":memory:")
        self.current_phase = SprintPhase.THINK
        self._restore_checkpoint()

    def _restore_checkpoint(self) -> None:
        try:
            rows = self.gbrain.search(CHECKPOINT_PROJECT, "sprint_phase=", limit=5)
        except Exception:
            return
        for row in rows:
            content = row.get("content") or ""
            if content.startswith("sprint_phase="):
                value = content.split("=", 1)[1].strip()
                try:
                    self.current_phase = SprintPhase(value)
                    return
                except ValueError:
                    continue

    def advance(self) -> SprintPhase:
        """Move to next phase. Wraps from REFLECT back to THINK."""
        idx = PHASE_ORDER.index(self.current_phase)
        self.current_phase = PHASE_ORDER[(idx + 1) % len(PHASE_ORDER)]
        return self.current_phase

    def set_phase(self, phase: SprintPhase | str) -> None:
        """Jump to any phase."""
        if isinstance(phase, str):
            phase = SprintPhase(phase.lower())
        if not isinstance(phase, SprintPhase):
            raise ValueError(f"Unknown phase: {phase}")
        self.current_phase = phase

    def available_personas(self) -> list[str]:
        """Return persona names active in current phase."""
        return list(PHASE_PERSONAS.get(self.current_phase, []))

    def available_commands(self) -> list[str]:
        """Return slash commands available in current phase (plus scout continuous)."""
        cmds = list(PHASE_COMMANDS.get(self.current_phase, []))
        for scout_cmd in ("/careful", "/freeze", "/guard", "/unfreeze"):
            if scout_cmd not in cmds:
                cmds.append(scout_cmd)
        return cmds

    def phase_summary(self) -> str:
        """Short summary: current phase, available personas/commands, next phase."""
        idx = PHASE_ORDER.index(self.current_phase)
        nxt = PHASE_ORDER[(idx + 1) % len(PHASE_ORDER)]
        personas = ", ".join(self.available_personas())
        commands = ", ".join(self.available_commands()[:8])
        return (
            f"Phase: {self.current_phase.value} | "
            f"Personas: {personas} | "
            f"Commands: {commands} | "
            f"Next: {nxt.value}"
        )

    def checkpoint(self) -> None:
        """Save current phase + context to gbrain so next session resumes here."""
        self.gbrain.save(
            CHECKPOINT_PROJECT,
            CHECKPOINT_PERSONA,
            CHECKPOINT_TYPE,
            f"sprint_phase={self.current_phase.value}",
        )
