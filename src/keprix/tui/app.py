"""Keprix Textual chat application."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.widgets import Footer, Header, Input, ListItem, ListView, Markdown, RichLog, Static

from keprix.tui.client import KeprixClient, ModelItem, SessionItem, SessionNotFoundError
from keprix.tui.clipboard import copy_text
from keprix.tui.composer import InputHistory, MessageQueue
from keprix.tui.formatting import agent_markdown, plain_text
from keprix.tui.slash_commands import dispatch_slash
from keprix.tui.streaming_markdown import StreamingMarkdownState
from keprix.tui.terminal_modes import reset_terminal_modes

THEME_PATH = Path(__file__).resolve().parent / "styles" / "theme.tcss"
SESSION_LIST_ITEM_PREFIX = "session-"
INTERRUPTED_SUFFIX = "\n\n*[interrupted]*"


def session_list_item_id(session_id: str) -> str:
    """Map API session UUID to a Textual-safe widget id."""
    return f"{SESSION_LIST_ITEM_PREFIX}{session_id}"


def session_id_from_list_item(widget_id: str) -> str:
    """Recover API session UUID from a session list widget id."""
    if widget_id.startswith(SESSION_LIST_ITEM_PREFIX):
        return widget_id[len(SESSION_LIST_ITEM_PREFIX) :]
    return widget_id


def _message_text(message: dict[str, Any]) -> str:
    role = message.get("role")
    prefix = "You" if role == "user" else "keprix"
    content = message.get("content")
    if isinstance(content, str):
        body = content.strip()
    elif isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                parts.append(str(block.get("content") or ""))
            elif block.get("type") == "tool_call":
                parts.append(f"[tool {block.get('name')}]")
        body = "\n".join(part for part in parts if part).strip()
    else:
        body = ""
    return f"{prefix}: {body}" if body else ""


class KeprixTuiApp(App):
    CSS_PATH = THEME_PATH
    TITLE = "keprix"
    BINDINGS = [
        Binding("ctrl+n", "new_chat", "New chat"),
        Binding("ctrl+s", "focus_sessions", "Sessions"),
        Binding("ctrl+m", "cycle_model", "Model"),
        Binding("ctrl+r", "reconnect", "Reconnect"),
        Binding("ctrl+shift+c", "copy_transcript", "Copy all"),
        Binding("ctrl+shift+l", "copy_last_reply", "Copy reply"),
        Binding("ctrl+shift+y", "copy_last_user", "Copy prompt"),
        Binding("ctrl+k", "flush_queue", "Send queue"),
        Binding("ctrl+c", "handle_ctrl_c", "Stop"),
    ]

    def __init__(
        self,
        *,
        client: KeprixClient,
        session_id: str | None = None,
        model: str | None = None,
    ) -> None:
        super().__init__()
        self.client = client
        if model:
            self.client.model = model
        self.session_id = session_id
        self.sessions: list[SessionItem] = []
        self.models: list[ModelItem] = []
        self.connected = False
        self.streaming = False
        self._thinking_lines: list[str] = []
        self._transcript_lines: list[str] = []
        self._last_user_text = ""
        self._last_agent_text = ""
        self._message_queue = MessageQueue()
        self._input_history = InputHistory()
        self._compose_lines: list[str] = []
        self._stream_text = ""
        self._stream_md_state = StreamingMarkdownState()
        self._md_stream = None
        self._turn_task: asyncio.Task[None] | None = None
        self._interrupt_requested = False

    def _input_bar(self) -> Input:
        return self.query_one("#input-bar", Input)

    def _stream_panel(self) -> Markdown:
        return self.query_one("#stream-panel", Markdown)

    def _set_busy(self, busy: bool) -> None:
        inp = self._input_bar()
        if busy:
            waiting = len(self._message_queue)
            suffix = f" ({waiting} queued)" if waiting else ""
            inp.placeholder = f"Agent working... type to queue{suffix} | Ctrl+C stop"
        else:
            inp.placeholder = "Message your agent... (/help for commands)"
            inp.focus()

    def _message_log(self) -> RichLog:
        return self.query_one("#message-log", RichLog)

    def _append_transcript(self, line: str) -> None:
        text = line.strip()
        if text:
            self._transcript_lines.append(text)

    def _log_system(self, line: str) -> None:
        self._append_transcript(line)
        self._message_log().write(f"[dim]{line}[/]")

    def _log_user_message(self, body: str) -> None:
        text = body.strip()
        if not text:
            return
        self._last_user_text = text
        self._append_transcript(f"You: {text}")
        log = self._message_log()
        log.write("")
        log.write("[bold #7EE787]> You[/]")
        log.write(plain_text(text))
        log.write("[dim #003B00]────────────────────────────────────────[/]")

    def _log_agent_message(self, body: str) -> None:
        text = body.strip()
        if not text:
            return
        self._last_agent_text = text
        self._append_transcript(f"keprix: {text}")
        log = self._message_log()
        log.write("[bold #79C0FF]keprix[/]")
        log.write(agent_markdown(text))
        log.write("")

    async def _begin_agent_stream(self) -> None:
        self._stream_text = ""
        self._stream_md_state.reset()
        panel = self._stream_panel()
        await panel.update("")
        panel.add_class("visible")
        self._md_stream = Markdown.get_stream(panel)

    async def _update_agent_stream(self, text: str) -> None:
        if not text or text == self._stream_text:
            return
        delta = text[len(self._stream_text) :]
        self._stream_text = text
        if delta and self._md_stream is not None:
            await self._md_stream.write(delta)

    async def _end_agent_stream(self) -> None:
        panel = self._stream_panel()
        if self._md_stream is not None:
            await self._md_stream.stop()
            self._md_stream = None
        panel.remove_class("visible")
        self._stream_text = ""
        self._stream_md_state.reset()

    def _log_rendered_message(self, line: str) -> None:
        if line.startswith("You: "):
            self._log_user_message(line[5:])
            return
        if line.startswith("keprix: "):
            self._log_agent_message(line[8:])
            return
        self._log_system(line)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Static("keprix", id="sidebar-title")
                yield ListView(id="session-list")
            with Vertical(id="chat-panel"):
                yield Static("New conversation", id="header")
                yield RichLog(id="message-log", wrap=True, highlight=False, markup=True)
                yield Static("", id="thinking-panel")
                yield Markdown("", id="stream-panel")
                yield Input(placeholder="Message your agent...", id="input-bar")
                yield Static("Connecting...", id="status-bar")
        yield Footer()

    async def on_mount(self) -> None:
        try:
            self.connected = await self.client.health_check()
        except httpx.HTTPError:
            self.connected = False
        if not self.connected:
            self.query_one("#status-bar", Static).update(
                "Backend offline. Start with: keprix start"
            )
            self._log_system(
                "keprix backend is not running at "
                f"{self.client.base_url}. Start it with `keprix start`."
            )
            return

        try:
            self.models = await self.client.list_models()
        except httpx.HTTPError as exc:
            self._net_error(exc)
            return
        if not self.client.model and self.models:
            self.client.model = self.models[0].id

        await self.refresh_sessions()
        preferred = self.session_id or (self.sessions[0].id if self.sessions else "")
        await self.load_session(preferred)

        self._update_status()
        self._input_bar().focus()

    async def on_unmount(self) -> None:
        reset_terminal_modes()

    async def on_key(self, event: Key) -> None:
        if not self._input_bar().has_focus:
            return
        if event.key == "up":
            current = self._input_bar().value
            self._input_history.begin_navigate(current)
            previous = self._input_history.previous()
            if previous is not None:
                self._input_bar().value = previous
                event.prevent_default()
                event.stop()
        elif event.key == "down":
            nxt = self._input_history.next()
            if nxt is not None:
                self._input_bar().value = nxt
                event.prevent_default()
                event.stop()

    async def refresh_sessions(self) -> None:
        try:
            self.sessions = await self.client.list_sessions()
        except httpx.HTTPError as exc:
            self._net_error(exc)
            return
        session_list = self.query_one("#session-list", ListView)
        await session_list.clear()
        items = [
            ListItem(
                Static(item.title[:36] or "Conversation"),
                id=session_list_item_id(item.id),
            )
            for item in self.sessions
        ]
        if items:
            await session_list.extend(items)

    async def load_session(self, session_id: str) -> bool:
        if self.streaming:
            self.notify("Wait for the current reply or press Ctrl+C to stop.")
            return False
        try:
            session_id = await self.client.ensure_ready_session(session_id)
        except httpx.HTTPError as exc:
            self._net_error(exc)
            return False
        self.session_id = session_id
        try:
            title, messages = await self.client.get_messages(session_id)
        except SessionNotFoundError:
            self.session_id = await self.client.ensure_ready_session(None)
            return await self.load_session(self.session_id)
        except httpx.HTTPError as exc:
            self._net_error(exc)
            return False
        self.query_one("#header", Static).update(title)
        log = self._message_log()
        log.clear()
        self._transcript_lines = []
        self._last_user_text = ""
        self._last_agent_text = ""
        self._message_queue.clear()
        if not messages:
            self._log_system("keprix")
            self._log_system("The Mutant AI OS")
            self._log_system("Type a message to begin. /help for commands.")
            self._log_system("Copy: Ctrl+Shift+L last reply | Ctrl+C stops a busy reply.")
        for message in messages:
            line = _message_text(message)
            if line:
                self._log_rendered_message(line)
        return True

    def _net_error(self, exc: Exception) -> None:
        msg = str(exc) or type(exc).__name__
        self._log_system(f"Network error: {msg}")
        self.query_one("#status-bar", Static).update("Backend unreachable. Is keprix running?")

    def _update_status(self) -> None:
        model_label = self.client.model or "no model"
        for item in self.models:
            if item.id == self.client.model:
                model_label = f"{item.provider}:{item.name}"
                break
        queue_note = f" | Queue: {len(self._message_queue)}" if self._message_queue else ""
        self.query_one("#status-bar", Static).update(
            f"Connected | Model: {model_label} | Sessions: {len(self.sessions)}{queue_note} | "
            "Ctrl+C stop | Ctrl+Shift+L copy"
        )

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item.id:
            await self.load_session(session_id_from_list_item(str(event.item.id)))

    async def _submit_text(self, text: str) -> None:
        if text.endswith("\\"):
            self._compose_lines.append(text[:-1].rstrip())
            self._input_bar().placeholder = "Next line... (submit without \\ to send)"
            return

        if self._compose_lines:
            self._compose_lines.append(text)
            text = "\n".join(self._compose_lines)
            self._compose_lines.clear()
            self._set_busy(self.streaming)

        text = text.strip()
        if not text:
            return

        if text.startswith("/"):
            result = await dispatch_slash(
                text,
                on_quit=self.action_quit_app,
                on_model=self.action_cycle_model,
                on_clear=self.action_clear_transcript,
                on_copy=self.action_copy_last_reply,
                on_interrupt=self.action_interrupt_turn,
                queue_snapshot=self._message_queue.snapshot,
            )
            if result.handled:
                if result.message:
                    self._log_system(result.message)
                return

        self._input_history.push(text)
        self._log_user_message(text)
        if self.streaming:
            self._message_queue.enqueue(text)
            self._set_busy(True)
            self.notify(f"Queued ({len(self._message_queue)} waiting). Ctrl+K sends next now.")
            return
        await self._start_turn(text)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if not self.connected:
            self._log_system("Backend offline. Press Ctrl+R to reconnect.")
            return
        if not self.session_id:
            return
        text = event.value
        event.input.value = ""
        await self._submit_text(text)

    async def _start_turn(self, text: str) -> None:
        if self._turn_task and not self._turn_task.done():
            self._message_queue.enqueue(text)
            return
        self._turn_task = asyncio.create_task(self._run_turn(text))
        try:
            await self._turn_task
        except asyncio.CancelledError:
            pass
        finally:
            self._turn_task = None

    async def _run_turn(self, text: str) -> None:
        thinking = self.query_one("#thinking-panel", Static)
        self.streaming = True
        self._interrupt_requested = False
        self._set_busy(True)
        thinking.update("")
        thinking.remove_class("visible")

        assistant_parts: list[str] = []
        streaming_visible = False
        retry = True
        try:
            while True:
                try:
                    async for payload in self._iter_turn(text):
                        if self._interrupt_requested:
                            raise asyncio.CancelledError()
                        kind = str(payload.get("event") or "")
                        if kind == "text_delta":
                            assistant_parts.append(str(payload.get("content") or ""))
                            body = "".join(assistant_parts)
                            if body and not streaming_visible:
                                await self._begin_agent_stream()
                                streaming_visible = True
                            if streaming_visible:
                                await self._update_agent_stream(body)
                            continue
                        if kind == "tool_call":
                            name = payload.get("name")
                            self._thinking_lines.append(f"running: {name}")
                            thinking.update("\n".join(self._thinking_lines))
                            thinking.add_class("visible")
                            continue
                        if kind == "tool_call_update":
                            self._thinking_lines.append(
                                f"{payload.get('status')}: {payload.get('name')}"
                            )
                            thinking.update("\n".join(self._thinking_lines))
                            continue
                        if kind == "message_done":
                            message = payload.get("message") or {}
                            line = _message_text(message)
                            if line.startswith("keprix: "):
                                assistant_parts = [line[8:]]
                            streaming_visible = False
                            await self._end_agent_stream()
                    break
                except SessionNotFoundError:
                    if not retry:
                        self._log_system("Error: session not found after retry.")
                        break
                    retry = False
                    assistant_parts = []
                    streaming_visible = False
                    await self._end_agent_stream()
                    self.session_id = await self.client.ensure_ready_session(None)
                    await self.refresh_sessions()
                    self._log_system(
                        "Note: previous session expired (backend may have restarted). Started a new chat."
                    )
        except asyncio.CancelledError:
            self._interrupt_requested = True
            await self._end_agent_stream()
        except Exception as exc:
            self._log_system(f"Error: {exc}")
            await self._end_agent_stream()

        reply = "".join(assistant_parts).strip()
        if reply:
            if streaming_visible:
                await self._end_agent_stream()
            if self._interrupt_requested:
                reply = f"{reply.rstrip()}{INTERRUPTED_SUFFIX}"
            self._log_agent_message(reply)
        elif self._interrupt_requested:
            self._log_system("Reply interrupted.")

        self._thinking_lines = []
        thinking.remove_class("visible")
        thinking.update("")
        self.streaming = False
        self._set_busy(False)
        await self.refresh_sessions()

        next_text = self._message_queue.pop()
        if next_text and not self._interrupt_requested:
            await self._start_turn(next_text)

    async def _iter_turn(self, text: str):
        if not self.session_id:
            return
        async for payload in self.client.stream_message(self.session_id, text):
            yield payload

    async def action_interrupt_turn(self) -> None:
        if not self.streaming:
            self.notify("Nothing to interrupt.")
            return
        self._interrupt_requested = True
        if self._turn_task and not self._turn_task.done():
            self._turn_task.cancel()
        self.notify("Stopping...")

    async def action_handle_ctrl_c(self) -> None:
        if self.streaming:
            await self.action_interrupt_turn()
            return
        if self._input_bar().value.strip() or self._compose_lines:
            self._input_bar().value = ""
            self._compose_lines.clear()
            self._set_busy(False)
            self.notify("Input cleared.")
            return
        await self.action_quit_app()

    async def action_flush_queue(self) -> None:
        if not self._message_queue:
            self.notify("Queue is empty.")
            return
        if self.streaming:
            await self.action_interrupt_turn()
            await asyncio.sleep(0)
        next_text = self._message_queue.pop()
        if next_text:
            await self._start_turn(next_text)

    async def action_clear_transcript(self) -> None:
        if self.streaming:
            self.notify("Stop the current reply before clearing.")
            return
        self._message_log().clear()
        self._transcript_lines.clear()
        self._log_system("Transcript cleared.")

    async def action_new_chat(self) -> None:
        if self.streaming:
            self.notify("Stop the current reply first (Ctrl+C).")
            return
        try:
            session = await self.client.create_session()
        except httpx.HTTPError as exc:
            self._net_error(exc)
            return
        await self.refresh_sessions()
        await self.load_session(session.id)
        self._update_status()

    async def action_reconnect(self) -> None:
        status = self.query_one("#status-bar", Static)
        status.update("Connecting...")
        try:
            self.connected = await self.client.health_check()
        except httpx.HTTPError:
            self.connected = False
        if not self.connected:
            self._log_system("Still offline. Is keprix running? (`keprix start`)")
            status.update("Backend offline. Start with: keprix start")
            return
        try:
            self.models = await self.client.list_models()
        except httpx.HTTPError as exc:
            self._net_error(exc)
            return
        if not self.client.model and self.models:
            self.client.model = self.models[0].id
        await self.refresh_sessions()
        if self.sessions:
            await self.load_session(self.sessions[0].id)
        else:
            self.session_id = await self.client.ensure_ready_session(None)
            await self.refresh_sessions()
            await self.load_session(self.session_id)
        self._update_status()
        self._log_system("Reconnected.")

    async def action_focus_sessions(self) -> None:
        self.query_one("#session-list", ListView).focus()

    async def action_cycle_model(self) -> None:
        if not self.models:
            return
        if not self.client.model:
            self.client.model = self.models[0].id
        else:
            ids = [item.id for item in self.models]
            index = ids.index(self.client.model) if self.client.model in ids else -1
            self.client.model = ids[(index + 1) % len(ids)]
        self._update_status()
        self.notify(f"Model: {self.client.model}")

    async def action_copy_transcript(self) -> None:
        if copy_text("\n".join(self._transcript_lines)):
            self.notify("Full transcript copied.")
        else:
            self.notify("Copy failed. Try Ctrl+Shift+L for the last reply only.")

    async def action_copy_last_reply(self) -> None:
        if not self._last_agent_text:
            self.notify("No assistant reply to copy yet.")
            return
        if copy_text(self._last_agent_text):
            self.notify("Last keprix reply copied.")
        else:
            self.notify("Copy failed. Install xclip or wl-clipboard.")

    async def action_copy_last_user(self) -> None:
        if not self._last_user_text:
            self.notify("No user message to copy yet.")
            return
        if copy_text(self._last_user_text):
            self.notify("Last prompt copied.")
        else:
            self.notify("Copy failed. Install xclip or wl-clipboard.")

    async def action_quit_app(self) -> None:
        reset_terminal_modes()
        await self.action_quit()
