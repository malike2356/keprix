"""Scout safety commands: /careful, /freeze, /guard, /unfreeze."""

from __future__ import annotations


class ScoutCommands:
    """Continuous safety layer. Independent of sprint phase.

    /careful: Raise caution level. Agent pauses before destructive ops.
    /freeze: Lock all file writes. Agent can read/search but not modify.
    /guard: Enable maximum safety. All tool calls require confirmation.
    /unfreeze: Release any active lock or guard.
    """

    CAUTION_LEVELS = ["normal", "careful", "guard"]

    DESTRUCTIVE_TOOLS = frozenset({"write_file", "patch", "terminal", "process", "delete_file"})

    def __init__(self):
        self.caution_level = "normal"
        self.frozen = False

    def careful(self) -> str:
        """Set caution to 'careful'. Agent asks before file writes and deletes."""
        self.caution_level = "careful"
        return "WARNING: Caution mode active. All destructive operations require confirmation."

    def freeze(self) -> str:
        """Lock all file writes. Read-only mode."""
        self.frozen = True
        return "Freeze active. All file writes blocked. Read/search only."

    def guard(self) -> str:
        """Maximum safety. Every tool call requires explicit user approval."""
        self.caution_level = "guard"
        return "Guard mode active. All tool calls require explicit approval."

    def unfreeze(self) -> str:
        """Release all locks."""
        self.caution_level = "normal"
        self.frozen = False
        return "Done: All locks released. Normal operations resumed."

    def should_block_write(self) -> bool:
        """Returns True if file writes should be blocked."""
        return self.frozen

    def should_confirm(self, tool_name: str) -> bool:
        """Returns True if this tool call requires user confirmation."""
        if self.caution_level == "guard":
            return True
        if self.caution_level == "careful" and tool_name in self.DESTRUCTIVE_TOOLS:
            return True
        return False

    def status(self) -> str:
        """Return current safety status as a single line."""
        return f"scout: caution={self.caution_level} frozen={self.frozen}"
