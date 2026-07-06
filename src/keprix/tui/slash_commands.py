"""Local slash commands for the Textual TUI (subset of Hermes SLASH_COMMANDS)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass
class SlashResult:
    handled: bool
    message: str = ""


SlashHandler = Callable[[list[str]], SlashResult | Awaitable[SlashResult]]


HELP_TEXT = """Local TUI commands:
  /help          this list
  /quit          exit
  /model         cycle model
  /clear         clear transcript
  /queue         show queued messages
  /copy          copy last reply
  /interrupt     stop current reply (same as Ctrl+C while busy)

Shortcuts:
  Ctrl+C         stop reply, clear input, or quit
  Ctrl+K         send next queued message now
  Ctrl+Shift+L   copy last reply
  Ctrl+Shift+C   copy full transcript
  Up/Down        input history (when line is empty)
  Ctrl+S         focus sessions"""


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
) -> SlashResult:
    command, _args = parse_slash(text)
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

    return SlashResult(
        handled=True,
        message=f"Unknown command {command}. Try /help.",
    )
