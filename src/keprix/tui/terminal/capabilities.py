"""Terminal capability exports."""

from keprix.tui.terminal_capabilities import (
    TerminalCapabilities,
    detect_terminal_capabilities,
    get_terminal_capabilities,
)

__all__ = ["TerminalCapabilities", "detect_terminal_capabilities", "get_terminal_capabilities"]
