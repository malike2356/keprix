"""Local slash commands for the Textual TUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from keprix.api.turn_registry import BUSY_INPUT_MODES


@dataclass
class SlashResult:
    handled: bool
    message: str = ""


SlashHandler = Callable[[list[str]], SlashResult | Awaitable[SlashResult]]


HELP_TEXT = """Local TUI commands:
  /help          this list (+ backend commands via fallthrough)
  /quit          exit
  /new           new chat
  /sessions      focus session list
  /model         cycle model
  /clear         clear transcript
  /queue         show queued messages
  /copy          copy last reply
  /interrupt     stop current reply (same as Ctrl+C while busy)
  /busy          show or set busy input mode (interrupt|queue|steer)
  /steer         inject guidance into the current turn
  /reconnect     reconnect to backend
  /mouse         toggle mouse capture
  /details       show or set details section modes
  /timeline      show or hide runtime event timeline
  /voice on|off  enable or disable push-to-talk
  /debug         toggle debug overlay when available
  /open <url>    open a URL in the system browser

Additional Hermes-style commands tab-complete and fall through to the backend:
  /compact /tools /skills /plugins /config /doctor /insights /resume /fork
  /theme /skin /export /import /feedback /profile /cron /gateway /agent
  /mcp /hub /billing /usage /status /restart
Docs: docs/reference/tui-slash.md

Shortcuts:
  Ctrl+C         stop reply, clear input, copy input selection, or quit
  Ctrl+P         command palette
  Ctrl+Space     command palette
  Ctrl+L         transcript search
  Ctrl+S         focus sessions
  Ctrl+M         model picker
  Ctrl+R         review mode
  Ctrl+Shift+R   reconnect to backend
  Ctrl+K         send next queued message now
  Ctrl+Shift+T   focus transcript (shift+arrows to select with --mouse)
  Ctrl+Shift+L   copy last reply
  Ctrl+Shift+C   copy selection or full transcript
  Ctrl+G         external editor compose
  Ctrl+B         push-to-talk voice (when enabled)
  ?              help
  Esc            close overlays
  Up/Down        input history (when line is empty)
  """


def parse_slash(text: str) -> tuple[str | None, list[str]]:
    raw = text.strip()
    if not raw.startswith("/"):
        return None, []
    parts = raw.split()
    return parts[0].lower(), parts[1:]


async def dispatch_slash(
    text: str,
    *,
    on_quit: Callable[[], Awaitable[None]],
    on_model: Callable[[], Awaitable[None]],
    on_clear: Callable[[], Awaitable[None]],
    on_copy: Callable[[], Awaitable[None]],
    on_interrupt: Callable[[], Awaitable[None]],
    queue_snapshot: Callable[[], list[str]],
    get_busy_mode: Callable[[], str] | None = None,
    set_busy_mode: Callable[[str], Awaitable[str]] | None = None,
    on_steer: Callable[[str], Awaitable[SlashResult]] | None = None,
    on_details: Callable[[list[str]], Awaitable[SlashResult]] | None = None,
    on_timeline: Callable[[list[str]], Awaitable[SlashResult]] | None = None,
    on_voice: Callable[[list[str]], Awaitable[SlashResult]] | None = None,
) -> SlashResult:
    command, args = parse_slash(text)
    if command is None:
        return SlashResult(handled=False)

    if command in {"/help", "/?"}:
        return SlashResult(handled=True, message=HELP_TEXT)

    if command in {"/quit", "/exit", "/q"}:
        await on_quit()
        return SlashResult(handled=True)

    if command == "/model":
        await on_model()
        return SlashResult(handled=True, message="Model cycled.")

    if command == "/clear":
        await on_clear()
        return SlashResult(handled=True, message="Transcript cleared.")

    if command == "/copy":
        await on_copy()
        return SlashResult(handled=True)

    if command in {"/interrupt", "/stop"}:
        await on_interrupt()
        return SlashResult(handled=True, message="Interrupted.")

    if command == "/queue":
        items = queue_snapshot()
        if not items:
            return SlashResult(handled=True, message="Queue is empty.")
        lines = [f"{idx + 1}. {item}" for idx, item in enumerate(items)]
        return SlashResult(handled=True, message="Queued:\n" + "\n".join(lines))

    if command == "/busy":
        if not args:
            mode = get_busy_mode() if get_busy_mode else "interrupt"
            return SlashResult(handled=True, message=f"Busy input mode: {mode}")
        mode = args[0].strip().lower()
        if mode not in BUSY_INPUT_MODES:
            return SlashResult(
                handled=True,
                message="Usage: /busy interrupt|queue|steer",
            )
        if set_busy_mode is None:
            return SlashResult(handled=True, message=f"Busy input mode: {mode}")
        applied = await set_busy_mode(mode)
        return SlashResult(handled=True, message=f"Busy input mode set to {applied}.")

    if command == "/steer":
        steer_text = " ".join(args).strip()
        if not steer_text:
            return SlashResult(handled=True, message="Usage: /steer <prompt>")
        if on_steer is None:
            return SlashResult(handled=True, message="Steer is unavailable.")
        return await on_steer(steer_text)

    if command == "/details":
        if on_details is None:
            return SlashResult(handled=True, message="Details view is unavailable.")
        return await on_details(args)

    if command == "/timeline":
        if on_timeline is None:
            return SlashResult(handled=True, message="Timeline view is unavailable.")
        return await on_timeline(args)

    if command == "/voice":
        if on_voice is None:
            return SlashResult(handled=True, message="Voice input is unavailable.")
        return await on_voice(args)

    if command == "/debug":
        return SlashResult(handled=True, message="Debug overlay is available through the TUI debug panel.")

    return SlashResult(handled=False)
