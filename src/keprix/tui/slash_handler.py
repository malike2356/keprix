"""Slash command handler with local registry and backend fallthrough."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

import httpx

from keprix.tui.client import KeprixClient
from keprix.tui.slash_commands import HELP_TEXT, SlashResult, dispatch_slash, parse_slash
from keprix.tui.slash_registry import canonical_local_command, is_local_slash_command


PAGER_LINE_THRESHOLD = 40
_SENSITIVE_CONTEXT_PREFIXES = (
    "user_id:",
    "workspace_id:",
    "role:",
    "channel:",
    "channel_user_id:",
)


@dataclass
class SlashDispatchResult:
    handled: bool
    message: str = ""
    pager: bool = False
    submit_text: str = ""
    alias_command: str = ""


def sanitize_slash_output(output: str) -> str:
    """Remove backend context/debug fields from user-visible slash output."""
    safe_lines: list[str] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            safe_lines.append(raw_line)
            continue
        if line.lower().startswith(_SENSITIVE_CONTEXT_PREFIXES):
            continue
        safe_lines.append(raw_line.replace("HTTPStatusError", "backend HTTP error"))
    return "\n".join(safe_lines).strip()


def command_unavailable_message(name: str) -> str:
    if name == "doctor":
        return "Doctor is not available from this backend. Run `keprix doctor` in a terminal or update the backend."
    return f"Command /{name} is not available from this backend. Try /help or update the backend."


async def dispatch_slash_with_fallthrough(
    text: str,
    *,
    client: KeprixClient,
    session_id: str | None,
    request_session_id: str | None,
    on_quit: Callable[[], Awaitable[None]],
    on_model: Callable[[], Awaitable[None]],
    on_clear: Callable[[], Awaitable[None]],
    on_copy: Callable[[], Awaitable[None]],
    on_interrupt: Callable[[], Awaitable[None]],
    on_new: Callable[[], Awaitable[None]] | None = None,
    on_sessions: Callable[[], Awaitable[None]] | None = None,
    on_reconnect: Callable[[], Awaitable[None]] | None = None,
    on_details: Callable[[list[str]], Awaitable[SlashResult]] | None = None,
    on_timeline: Callable[[list[str]], Awaitable[SlashResult]] | None = None,
    on_voice: Callable[[list[str]], Awaitable[SlashResult]] | None = None,
    on_toggle_mouse: Callable[[], Awaitable[None]] | None = None,
    queue_snapshot: Callable[[], list[str]],
    get_busy_mode: Callable[[], str] | None = None,
    set_busy_mode: Callable[[str], Awaitable[str]] | None = None,
    on_steer: Callable[[str], Awaitable[SlashResult]] | None = None,
) -> SlashDispatchResult:
    command, _args = parse_slash(text)
    if command is None:
        return SlashDispatchResult(handled=False)
    canonical = canonical_local_command(command)
    if canonical and canonical != command:
        text = text.replace(command, canonical, 1)
        command = canonical

    if is_local_slash_command(command):
        if command in {"/new"} and on_new is not None:
            await on_new()
            return SlashDispatchResult(handled=True, message="Started a new chat.")
        if command == "/sessions" and on_sessions is not None:
            await on_sessions()
            return SlashDispatchResult(handled=True, message="Focused session list.")
        if command == "/reconnect" and on_reconnect is not None:
            await on_reconnect()
            return SlashDispatchResult(handled=True, message="Reconnect attempted.")
        if command in {"/details", "/timeline"}:
            local = await dispatch_slash(
                text,
                on_quit=on_quit,
                on_model=on_model,
                on_clear=on_clear,
                on_copy=on_copy,
                on_interrupt=on_interrupt,
                queue_snapshot=queue_snapshot,
                get_busy_mode=get_busy_mode,
                set_busy_mode=set_busy_mode,
                on_steer=on_steer,
                on_details=on_details,
                on_timeline=on_timeline,
                on_voice=on_voice,
            )
            return SlashDispatchResult(handled=local.handled, message=local.message)
        if command == "/voice":
            local = await dispatch_slash(
                text,
                on_quit=on_quit,
                on_model=on_model,
                on_clear=on_clear,
                on_copy=on_copy,
                on_interrupt=on_interrupt,
                queue_snapshot=queue_snapshot,
                get_busy_mode=get_busy_mode,
                set_busy_mode=set_busy_mode,
                on_steer=on_steer,
                on_details=on_details,
                on_timeline=on_timeline,
                on_voice=on_voice,
            )
            return SlashDispatchResult(handled=local.handled, message=local.message)
        if command == "/mouse" and on_toggle_mouse is not None:
            await on_toggle_mouse()
            return SlashDispatchResult(handled=True)

        local = await dispatch_slash(
            text,
            on_quit=on_quit,
            on_model=on_model,
            on_clear=on_clear,
            on_copy=on_copy,
            on_interrupt=on_interrupt,
            queue_snapshot=queue_snapshot,
            get_busy_mode=get_busy_mode,
            set_busy_mode=set_busy_mode,
            on_steer=on_steer,
            on_details=on_details,
            on_timeline=on_timeline,
            on_voice=on_voice,
        )
        if local.handled:
            return SlashDispatchResult(handled=True, message=local.message)

    if not session_id:
        return SlashDispatchResult(handled=True, message="No active session for backend slash commands.")

    exec_result = await client.slash_exec(text.lstrip("/"), session_id=session_id)
    if request_session_id and session_id != request_session_id:
        return SlashDispatchResult(handled=True, message="")

    if exec_result.get("ok"):
        output = sanitize_slash_output(str(exec_result.get("output") or ""))
        pager = bool(exec_result.get("pager")) or output.count("\n") + 1 > PAGER_LINE_THRESHOLD
        return SlashDispatchResult(handled=True, message=output, pager=pager)

    if not exec_result.get("fallthrough"):
        output = sanitize_slash_output(str(exec_result.get("output") or "Slash command failed."))
        if output:
            pager = output.count("\n") + 1 > PAGER_LINE_THRESHOLD
            return SlashDispatchResult(handled=True, message=output, pager=pager)
        return SlashDispatchResult(handled=True, message="Slash command failed.")

    name = text.lstrip("/").split()[0]
    arg = text.lstrip("/")[len(name) :].strip()
    try:
        dispatch = await client.command_dispatch(name, arg, session_id=session_id)
    except httpx.HTTPError as exc:
        return SlashDispatchResult(
            handled=True,
            message=command_unavailable_message(name),
        )
    if request_session_id and session_id != request_session_id:
        return SlashDispatchResult(handled=True, message="")

    dispatch_type = str(dispatch.get("type") or "exec")
    if dispatch_type == "alias":
        target = str(dispatch.get("target") or name)
        alias_text = f"/{target}{f' {arg}' if arg else ''}"
        return SlashDispatchResult(handled=True, alias_command=alias_text)
    if dispatch_type in {"send", "skill"}:
        submit = str(dispatch.get("message") or "").strip()
        if not submit:
            return SlashDispatchResult(handled=True, message="Command returned an empty message.")
        label = str(dispatch.get("name") or name) if dispatch_type == "skill" else name
        return SlashDispatchResult(
            handled=True,
            message=f"Running /{label}...",
            submit_text=submit,
        )
    output = sanitize_slash_output(str(dispatch.get("output") or "")) or "(no output)"
    pager = output.count("\n") + 1 > PAGER_LINE_THRESHOLD
    return SlashDispatchResult(handled=True, message=output, pager=pager)
