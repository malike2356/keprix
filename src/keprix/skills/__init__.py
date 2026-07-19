"""Keprix skill system orchestrator (gstack-compatible)."""

from __future__ import annotations

from keprix.memory.gbrain import GBrain
from keprix.skills.preamble_loader import PreambleLoader
from keprix.skills.scout_commands import ScoutCommands
from keprix.skills.sprint_flow import SHIP_COMMANDS, SprintFlow, SprintPhase
from keprix.skills.trigger_engine import TriggerEngine

__all__ = [
    "KeprixSkills",
    "PreambleLoader",
    "TriggerEngine",
    "SprintFlow",
    "SprintPhase",
    "ScoutCommands",
    "GBrain",
]


class KeprixSkills:
    """Top-level orchestrator for the Keprix skill system."""

    def __init__(self, personas_dir: str, gbrain_db: str):
        self.preamble = PreambleLoader(personas_dir)
        self.triggers = TriggerEngine(personas_dir)
        self.gbrain = GBrain(gbrain_db)
        self.sprint = SprintFlow(self.gbrain)
        self.scout = ScoutCommands()

    def handle_input(self, user_text: str) -> dict:
        """
        Main entry point. Given user input:
        1. Check if it's a Scout safety command → handle immediately
        2. Route to persona via TriggerEngine
        3. Load context via PreambleLoader (tier 2 + tier 3)
        4. Gate ship commands to SHIP phase
        5. Return persona name, command, context, and sprint status
        """
        text = (user_text or "").strip()
        routed = self.triggers.route(text)

        if routed and routed[0] == "scout":
            persona, command = routed
            message = self._run_scout(command)
            return {
                "mode": "scout",
                "persona": persona,
                "command": command,
                "message": message,
                "frozen": self.scout.frozen,
                "caution_level": self.scout.caution_level,
                "sprint": self.sprint.phase_summary(),
            }

        if not routed:
            return {
                "mode": "default",
                "persona": None,
                "command": None,
                "context": self.preamble.tier_1_context(),
                "sprint": self.sprint.phase_summary(),
                "message": "Default assistant mode (no persona override).",
            }

        persona, command = routed

        if command in SHIP_COMMANDS and self.sprint.current_phase != SprintPhase.SHIP:
            return {
                "mode": "error",
                "persona": persona,
                "command": command,
                "error": "Not in SHIP phase. Advance first.",
                "sprint": self.sprint.phase_summary(),
            }

        tier2 = self.preamble.tier_2_context(self.sprint.current_phase.value)
        tier3 = self.preamble.tier_3_context(command)
        context = "\n\n".join(p for p in (tier2, tier3) if p)

        return {
            "mode": "persona",
            "persona": persona,
            "command": command,
            "context": context,
            "sprint": self.sprint.phase_summary(),
            "phase": self.sprint.current_phase.value,
        }

    def _run_scout(self, command: str) -> str:
        mapping = {
            "/careful": self.scout.careful,
            "/freeze": self.scout.freeze,
            "/guard": self.scout.guard,
            "/unfreeze": self.scout.unfreeze,
        }
        fn = mapping.get(command)
        if not fn:
            return f"Unknown scout command: {command}"
        return fn()

    def phase_summary(self) -> str:
        """Human-readable summary of current sprint state."""
        return self.sprint.phase_summary()
