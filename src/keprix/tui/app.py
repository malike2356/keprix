"""Keprix Textual chat application."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import httpx
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key, Resize
from textual.widgets import Input, ListItem, ListView, Markdown, Static

from keprix.tui.client import KeprixClient, ModelItem, RegistryItem, SessionItem, SessionNotFoundError, SteerNotBusyError
from keprix.tui.clipboard import copy_text
from keprix.tui.composer import InputHistory, MessageQueue
from keprix.tui.details import (
    ActivityFeed,
    DetailsConfig,
    SubagentList,
    ToolTrail,
    cycle_mode,
    parse_section_mode,
    parse_section_name,
    render_details_panel,
)
from keprix.tui.details_runtime import render_runtime_details
from keprix.tui.external_editor import edit_in_editor, resolve_editor
from keprix.tui.external_link import open_external_link
from keprix.tui.history_search import search_history
from keprix.tui.command_center.palette import CommandPaletteModel, dispatch_for_action
from keprix.tui.command_center.cockpit import build_cockpit_state
from keprix.tui.command_center.review import build_review_report
from keprix.tui.command_center.runtime_timeline import RuntimeTimelineEvent
from keprix.tui.command_center.registry import build_default_registry
from keprix.tui.command_center.status import StatusSnapshot
from keprix.tui.sessions.map import build_session_map
from keprix.tui.paste_snip import PasteSnipStore, collapsed_paste_placeholder, line_count, should_collapse_paste
from keprix.tui.preferences import load_busy_input_override, load_theme_preference, save_busy_input_override, save_theme_preference
from keprix.tui.setup_handoff import run_setup_handoff
from keprix.tui.slash_commands import SlashResult, parse_slash
from keprix.tui.slash_handler import dispatch_slash_with_fallthrough
from keprix.tui.runtime_events import ApiRuntimeEvent, MessageRuntimeMetadata, PluginRuntimeItem, SkillRuntimeItem
from keprix.tui.runtime_store import RuntimeStore
from keprix.tui.runtime_transport import HttpRuntimeTransport
from keprix.tui.streaming_markdown import StreamingMarkdownState
from keprix.tui.terminal_modes import reset_terminal_modes
from keprix.tui.graceful_exit import register_exit_handlers
from keprix.tui.debug_overlay import DebugOverlayState
from keprix.tui.widgets.top_bar import TopBar
from keprix.tui.widgets.status_bar import StatusBar
from keprix.tui.terminal_capabilities import get_terminal_capabilities
from keprix.tui.theme_system import available_themes, normalize_theme_name, theme_class_names, theme_tokens
from keprix.tui.alternate_screen import set_window_title
from keprix.tui.thinking_block import ThinkingBlockManager
from keprix.tui.tool_progress import ToolProgressTracker
from keprix.tui.hardening import state_for_http_status, terminal_too_small
from keprix.tui.voice import VoiceCaptureError, VoiceRecorder, voice_backend_label
from keprix.tui.widgets.approval_overlay import ApprovalOverlay
from keprix.tui.widgets.clarify_overlay import ClarifyOverlay
from keprix.tui.widgets.command_palette import CommandPalette
from keprix.tui.widgets.help_overlay import render_help_overlay
from keprix.tui.widgets.pager_screen import PagerScreen
from keprix.tui.widgets.runtime_timeline import RuntimeTimelineWidget
from keprix.tui.widgets.review_mode import ReviewMode
from keprix.tui.widgets.session_map import SessionMapWidget
from keprix.tui.widgets.setup_required import SetupRequiredOverlay
from keprix.tui.widgets.slash_input import SlashInput
from keprix.tui.widgets.slash_input import SlashCompletionOption
from keprix.tui.widgets.virtual_transcript import VirtualTranscript
from keprix.tui.widgets.workspace_cockpit import WorkspaceCockpit
from keprix.api.web_ui_prompt_bridge import get_tui_clarify_timeout_sec

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
        Binding("ctrl+p", "command_palette", "Command palette"),
        Binding("ctrl+space", "command_palette", "Command palette"),
        Binding("ctrl+s", "focus_sessions", "Sessions"),
        Binding("ctrl+m", "cycle_model", "Model"),
        Binding("ctrl+r", "review_mode", "Review"),
        Binding("ctrl+shift+r", "reconnect", "Reconnect"),
        Binding("ctrl+l", "search_transcript", "Search"),
        Binding("?", "help", "Help"),
        Binding("ctrl+shift+c", "copy_transcript", "Copy"),
        Binding("ctrl+shift+t", "focus_transcript", "Transcript"),
        Binding("ctrl+shift+l", "copy_last_reply", "Copy reply"),
        Binding("ctrl+shift+y", "copy_last_user", "Copy prompt"),
        Binding("ctrl+k", "flush_queue", "Send queue"),
        Binding("ctrl+c", "handle_ctrl_c", "Stop"),
        Binding("pageup", "transcript_page_up", "Scroll up"),
        Binding("pagedown", "transcript_page_down", "Scroll down"),
        Binding("home", "transcript_home", "Top"),
        Binding("end", "transcript_end", "Bottom"),
        Binding("ctrl+home", "transcript_first", "First message"),
        Binding("ctrl+g", "external_editor", "Editor"),
        Binding("ctrl+b", "voice_toggle", "Voice"),
    ]

    def __init__(
        self,
        *,
        client: KeprixClient,
        session_id: str | None = None,
        model: str | None = None,
        mouse_enabled: bool = False,
    ) -> None:
        super().__init__()
        self.client = client
        self.transport = HttpRuntimeTransport(client)
        self._mouse_enabled = mouse_enabled
        if model:
            self.client.model = model
        self.session_id = session_id
        self.sessions: list[SessionItem] = []
        self.models: list[ModelItem] = []
        self.connected = False
        self.streaming = False
        self._details_config = DetailsConfig()
        self._details_panel_visible = False
        self._timeline_panel_visible = False
        self._tool_trail = ToolTrail()
        self._subagents = SubagentList()
        self._activity_feed = ActivityFeed()
        self._paste_snips = PasteSnipStore()
        self._voice_recorder = VoiceRecorder()
        self._voice_enabled = True
        self._compose_key = "ctrl+g"
        self._voice_record_key = "ctrl+b"
        self._last_user_text = ""
        self._last_agent_text = ""
        self._prompt_queue = MessageQueue()
        self._input_history = InputHistory()
        self._compose_lines: list[str] = []
        self._stream_text = ""
        self._stream_md_state = StreamingMarkdownState()
        self._thinking_mgr = ThinkingBlockManager()
        self._tool_progress = ToolProgressTracker()
        self._md_stream = None
        self._turn_task: asyncio.Task[None] | None = None
        self._interrupt_requested = False
        self._pending_after_interrupt = ""
        self._config_busy_mode = "interrupt"
        self._local_busy_mode = load_busy_input_override()
        self._prompt_overlay_open = False
        self._completion_hint = ""
        self._setup_required = os.environ.get("KEPRIX_SETUP_REQUIRED") == "1"
        self._debug_state = DebugOverlayState()
        self._runtime_store = RuntimeStore()
        self._theme_name = load_theme_preference()
        self._voice_state = "off"

    def _input_bar(self) -> SlashInput:
        return self.query_one("#input-bar", SlashInput)

    def _stream_panel(self) -> Markdown:
        return self.query_one("#stream-panel", Markdown)

    def _effective_busy_mode(self) -> str:
        return self._local_busy_mode or self._config_busy_mode or "interrupt"

    def _apply_theme(self) -> None:
        for class_name in theme_class_names():
            self.remove_class(class_name)
        self.add_class(theme_tokens(self._theme_name).class_name)

    def _set_theme(self, theme_name: str) -> str:
        self._theme_name = save_theme_preference(theme_name)
        if self.is_mounted and getattr(self, "_screen_stack", None):
            self._apply_theme()
            self._update_status()
        return self._theme_name

    def _help_text(self) -> str:
        return render_help_overlay()

    def _set_busy(self, busy: bool) -> None:
        inp = self._input_bar()
        if busy:
            mode = self._effective_busy_mode()
            waiting = len(self._prompt_queue)
            if mode == "steer":
                inp.placeholder = "Agent working... type to steer | Ctrl+C stop"
            elif mode == "queue":
                suffix = f" ({waiting} queued)" if waiting else ""
                inp.placeholder = f"Agent working... type to queue{suffix} | Ctrl+C stop"
            else:
                inp.placeholder = "Agent working... Enter interrupts | Ctrl+C stop"
        else:
            inp.placeholder = "Message your agent... (/help for commands)"
            inp.focus()

    def _message_log(self) -> VirtualTranscript:
        return self.query_one("#message-log", VirtualTranscript)

    def _cockpit(self) -> WorkspaceCockpit:
        return self.query_one("#workspace-cockpit", WorkspaceCockpit)

    def _log_system(self, line: str) -> None:
        self._hide_cockpit()
        self._message_log().append_system(line)

    def _log_user_message(self, body: str) -> None:
        text = body.strip()
        if not text:
            return
        self._hide_cockpit()
        self._last_user_text = text
        self._message_log().append_user(text)

    def _log_agent_message(self, body: str) -> None:
        text = body.strip()
        if not text:
            return
        self._hide_cockpit()
        self._last_agent_text = text
        self._message_log().append_agent(text)

    def _hide_cockpit(self) -> None:
        try:
            self._cockpit().update_state(self._build_cockpit_state(), visible=False)
        except Exception:
            pass

    def _build_cockpit_state(self):
        skills = [
            RegistryItem(item.name, item.description, item.installed, item.enabled, item.source)
            for item in self._runtime_store.skills
        ]
        plugins = [
            RegistryItem(item.name, item.description, item.installed, item.enabled, item.source, item.version)
            for item in self._runtime_store.plugins
        ]
        return build_cockpit_state(
            session_id=self.session_id or "",
            sessions=self.sessions,
            model=self.client.model or "",
            models=self.models,
            transport_mode=getattr(self.transport, "mode", "unknown"),
            connected=self.connected,
            queue_depth=len(self._prompt_queue),
            skills=skills,
            plugins=plugins,
            setup_required=self._setup_required,
        )

    def _refresh_cockpit(self, *, force_visible: bool = False) -> None:
        try:
            visible = force_visible or not self._message_log().store.items
            self._cockpit().update_state(self._build_cockpit_state(), visible=visible)
        except Exception:
            pass

    async def _begin_agent_stream(self) -> None:
        self._stream_text = ""
        self._stream_md_state.reset()
        self._thinking_mgr = ThinkingBlockManager()
        self._tool_progress = ToolProgressTracker()
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
        yield TopBar(session_title="New conversation")
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Static("Workspace", id="sidebar-title")
                yield Static("", id="sidebar-status")
                yield Static("Sessions", id="sidebar-section")
                yield ListView(id="session-list")
                yield SessionMapWidget("", id="session-map")
                yield Static("", id="sidebar-help")
            with Vertical(id="chat-panel"):
                yield Static("New conversation", id="header")
                yield WorkspaceCockpit("", id="workspace-cockpit")
                yield VirtualTranscript(
                    id="message-log",
                    mouse_selection_enabled=self._mouse_enabled,
                )
                yield Static("", id="thinking-panel")
                yield RuntimeTimelineWidget("", id="runtime-timeline")
                yield Markdown("", id="stream-panel")
                yield Static("", id="slash-suggestions")
                yield SlashInput(placeholder="Message your agent...", id="input-bar")
        yield StatusBar()

    async def on_mount(self) -> None:
        self._apply_theme()
        caps = get_terminal_capabilities()
        if terminal_too_small(self.size.width, self.size.height):
            self._log_system("Terminal too small. Resize to at least 40 columns by 10 rows.")
        register_exit_handlers(save_last_session_id=self.session_id)

        try:
            self.connected = await self.client.health_check()
        except httpx.HTTPError:
            self.connected = False
        if not self.connected:
            self._status_bar().set_connected(False)
            self._log_system(
                "keprix backend is not running at "
                f"{self.client.base_url}. Start it with `keprix start`."
            )
            return

        if await self._ensure_provider_configured():
            await self.action_quit_app()
            return

        await self._maybe_show_openclaw_banner()

        try:
            self.models = await self.transport.list_models()
        except httpx.HTTPError as exc:
            self._net_error(exc)
            return
        if not self.client.model and self.models:
            self.client.model = self.models[0].id

        await self.refresh_sessions()
        await self._refresh_runtime_registries()
        preferred = self.session_id or (self.sessions[0].id if self.sessions else "")
        await self.load_session(preferred)

        await self._load_tui_config()
        input_bar = self._input_bar()
        input_bar._complete_slash = self._complete_slash_prefix  # type: ignore[attr-defined]
        input_bar._on_completion_hint = self._set_completion_hint  # type: ignore[attr-defined]
        input_bar._on_completion_candidates = self._set_completion_candidates  # type: ignore[attr-defined]
        input_bar._on_paste_text = self._handle_paste_text  # type: ignore[attr-defined]
        self._update_status()
        self._update_sidebar()
        self._refresh_cockpit(force_visible=True)
        self._input_bar().focus()

    async def _refresh_runtime_registries(self) -> None:
        try:
            skills = await self.transport.list_skills()
        except Exception:
            skills = []
        try:
            plugins = await self.transport.list_plugins()
        except Exception:
            plugins = []
        self._runtime_store.set_skills(
            [
                SkillRuntimeItem(
                    name=item.name,
                    description=item.description,
                    installed=item.installed,
                    enabled=item.enabled,
                    source=item.source,
                )
                for item in skills
            ]
        )
        self._runtime_store.set_plugins(
            [
                PluginRuntimeItem(
                    name=item.name,
                    description=item.description,
                    version=item.version,
                    installed=item.installed,
                    enabled=item.enabled,
                    source=item.source,
                )
                for item in plugins
            ]
        )
        self._refresh_cockpit()

    def _set_composer_enabled(self, enabled: bool) -> None:
        self._input_bar().disabled = not enabled

    async def _save_minimal_setup(
        self,
        provider: str,
        api_key: str,
        base_url: str,
        model: str,
    ) -> tuple[bool, str]:
        try:
            await self.client.save_minimal_setup(
                provider=provider,
                api_key=api_key,
                base_url=base_url,
                model=model,
            )
            return True, "Provider saved."
        except Exception as exc:
            return False, f"Setup failed: {exc}"

    async def _run_setup_handoff_async(self, section: str = "") -> int:
        import asyncio

        async with self.suspend():
            return await asyncio.to_thread(run_setup_handoff, section)

    async def _ensure_provider_configured(self) -> bool:
        """Return True when the user exits without configuring a provider."""
        while True:
            try:
                status = await self.client.fetch_setup_status()
            except httpx.HTTPError as exc:
                self._net_error(exc)
                return True
            if status.get("provider_configured"):
                self._setup_required = False
                os.environ.pop("KEPRIX_SETUP_REQUIRED", None)
                self._set_composer_enabled(True)
                return False

            self._setup_required = True
            self._set_composer_enabled(False)
            providers = status.get("minimal_providers") or []
            docs_url = str(status.get("docs_url") or "")
            result = await self.push_screen_wait(
                SetupRequiredOverlay(
                    providers=providers,
                    docs_url=docs_url,
                    on_save=self._save_minimal_setup,
                    on_handoff=self._run_setup_handoff_async,
                )
            )
            if isinstance(result, dict) and result.get("ok"):
                continue
            return True

    async def _maybe_show_openclaw_banner(self) -> None:
        try:
            from agent.onboarding import (
                OPENCLAW_RESIDUE_FLAG,
                detect_openclaw_residue,
                is_seen,
                mark_seen,
                openclaw_residue_hint_cli,
            )
            from keprix_cli.config import get_config_path, load_config
        except Exception:
            return
        cfg = load_config()
        if not detect_openclaw_residue() or is_seen(cfg, OPENCLAW_RESIDUE_FLAG):
            return
        self._log_system(openclaw_residue_hint_cli())
        mark_seen(get_config_path(), OPENCLAW_RESIDUE_FLAG)

    async def _refresh_after_setup(self) -> None:
        if await self._ensure_provider_configured():
            return
        try:
            self.models = await self.transport.list_models()
        except httpx.HTTPError:
            self.models = []
        if not self.client.model and self.models:
            self.client.model = self.models[0].id
        self._update_status()

    def _handle_paste_text(self, pasted: str) -> str | None:
        if not should_collapse_paste(pasted):
            return None
        placeholder = collapsed_paste_placeholder(line_count(pasted))
        self._paste_snips.store(placeholder, pasted)
        return placeholder

    def _expand_submit_text(self, text: str) -> str:
        return self._paste_snips.expand(text).strip()

    def _thinking_panel(self) -> Static:
        return self.query_one("#thinking-panel", Static)

    def _timeline_panel(self) -> RuntimeTimelineWidget:
        return self.query_one("#runtime-timeline", RuntimeTimelineWidget)

    def _refresh_runtime_timeline(self) -> None:
        try:
            self._timeline_panel().update_timeline(
                self._runtime_store.timeline,
                visible=self._timeline_panel_visible and bool(self._runtime_store.timeline.events),
            )
        except Exception:
            pass

    def _refresh_thinking_panel(self) -> None:
        panel = self._thinking_panel()
        if not self._details_panel_visible:
            panel.update("")
            panel.remove_class("visible")
            self._refresh_runtime_timeline()
            self._update_sidebar()
            return
        rendered = render_details_panel(
            config=self._details_config,
            trail=self._tool_trail,
            subagents=self._subagents,
            activity=self._activity_feed,
        )
        runtime_rendered = render_runtime_details(self._runtime_store)
        if runtime_rendered.strip():
            rendered = f"{runtime_rendered}\n{rendered}" if rendered.strip() else runtime_rendered
        if rendered.strip():
            panel.update(rendered)
            panel.add_class("visible")
        else:
            panel.update("")
            panel.remove_class("visible")
        self._refresh_runtime_timeline()
        self._update_sidebar()

    async def _slash_details(self, args: list[str]) -> SlashResult:
        if not args:
            self._details_panel_visible = True
            self._refresh_thinking_panel()
            return SlashResult(
                handled=True,
                message=f"{self._details_config.format_status()}\nUse /details hide to close the panel.",
            )
        if len(args) == 1 and args[0].lower() in {"hide", "off", "close"}:
            self._details_panel_visible = False
            self._refresh_thinking_panel()
            return SlashResult(handled=True, message="Details panel hidden.")
        if len(args) == 1 and args[0].lower() in {"show", "on", "open"}:
            self._details_panel_visible = True
            self._refresh_thinking_panel()
            return SlashResult(handled=True, message="Details panel shown.")
        if len(args) == 1 and args[0].lower() == "all":
            return SlashResult(
                handled=True,
                message="Usage: /details all hidden|collapsed|expanded",
            )
        if len(args) == 2 and args[0].lower() == "all":
            mode = parse_section_mode(args[1])
            if mode is None:
                return SlashResult(
                    handled=True,
                    message="Usage: /details all hidden|collapsed|expanded",
                )
            self._details_config.set_all(mode)
            self._details_panel_visible = True
            self._refresh_thinking_panel()
            return SlashResult(handled=True, message=f"All details sections set to {mode}.")
        if len(args) == 2:
            section = parse_section_name(args[0])
            mode = parse_section_mode(args[1])
            if section is None or mode is None:
                return SlashResult(
                    handled=True,
                    message="Usage: /details [thinking|tools|subagents|activity mode]",
                )
            self._details_config.set_mode(section, mode)
            self._details_panel_visible = True
            self._refresh_thinking_panel()
            return SlashResult(
                handled=True,
                message=f"Details section {section} set to {mode}.",
            )
        return SlashResult(handled=True, message=self._details_config.format_status())

    async def _slash_timeline(self, args: list[str]) -> SlashResult:
        if args and args[0].lower() in {"hide", "off", "close"}:
            self._timeline_panel_visible = False
            self._refresh_runtime_timeline()
            return SlashResult(handled=True, message="Runtime timeline hidden.")
        self._timeline_panel_visible = True
        self._refresh_runtime_timeline()
        if not self._runtime_store.timeline.events:
            return SlashResult(handled=True, message="Runtime timeline is empty.")
        return SlashResult(handled=True, message="Runtime timeline shown. Use /timeline hide to close it.")

    async def _slash_voice(self, args: list[str]) -> SlashResult:
        if not args:
            state = "on" if self._voice_enabled else "off"
            return SlashResult(
                handled=True,
                message=f"Voice input: {state} ({voice_backend_label()})",
            )
        flag = args[0].strip().lower()
        if flag in {"on", "enable", "true", "1"}:
            self._voice_enabled = True
            self._update_status()
            return SlashResult(handled=True, message="Voice input enabled.")
        if flag in {"off", "disable", "false", "0"}:
            self._voice_enabled = False
            if self._voice_recorder.recording:
                try:
                    self._voice_recorder.stop()
                except VoiceCaptureError:
                    pass
            self._update_status()
            return SlashResult(handled=True, message="Voice input disabled.")
        return SlashResult(handled=True, message="Usage: /voice on|off")

    async def _load_tui_config(self) -> None:
        try:
            cfg = await self.transport.get_tui_config()
            self._config_busy_mode = cfg.busy_input_mode
            self._details_config = DetailsConfig.from_mapping(cfg.details_modes)
            self._compose_key = cfg.compose_key
            self._voice_record_key = cfg.voice_record_key
            self._voice_enabled = cfg.voice_enabled
        except Exception:
            self._config_busy_mode = "interrupt"

    async def on_unmount(self) -> None:
        reset_terminal_modes()

    async def on_key(self, event: Key) -> None:
        if self._prompt_overlay_open and event.key in {"pageup", "pagedown"}:
            log = self._message_log()
            if event.key == "pageup":
                log.scroll_page_up()
            else:
                log.scroll_page_down()
            event.stop()
            return
        if not self._input_bar().has_focus:
            return
        if self._input_bar().value.startswith("/") and event.key in {"up", "down"}:
            step = -1 if event.key == "up" else 1
            if await self._input_bar().cycle_completion(step):
                event.prevent_default()
                event.stop()
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

    async def on_resize(self, event: Resize) -> None:
        self._debug_state.log_event(f"resize {event.size.width}x{event.size.height}")
        self._refresh_thinking_panel()
        self._update_sidebar()

    async def refresh_sessions(self) -> None:
        try:
            self.sessions = await self.transport.list_sessions()
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
        self._update_sidebar()

    async def load_session(self, session_id: str) -> bool:
        if self.streaming:
            self.notify("Wait for the current reply or press Ctrl+C to stop.")
            return False
        try:
            session_id = await self.transport.ensure_ready_session(session_id)
        except httpx.HTTPError as exc:
            self._net_error(exc)
            return False
        self.session_id = session_id
        try:
            title, messages = await self.transport.get_messages(session_id)
        except SessionNotFoundError:
            self.session_id = await self.transport.ensure_ready_session(None)
            return await self.load_session(self.session_id)
        except httpx.HTTPError as exc:
            self._net_error(exc)
            return False
        self.query_one("#header", Static).update(title)
        self._top_bar().update_title(title)
        set_window_title(f"keprix - {title}")
        log = self._message_log()
        log.clear()
        self._last_user_text = ""
        self._last_agent_text = ""
        self._prompt_queue.clear()
        log.begin_batch()
        if not messages:
            self._refresh_cockpit(force_visible=True)
        for message in messages:
            line = _message_text(message)
            if line:
                self._log_rendered_message(line)
        log.end_batch()
        if log.store.archived_warning:
            self._log_system("Transcript trimmed to recent history (5000 message cap).")
        self._update_sidebar()
        self._refresh_cockpit(force_visible=not messages)
        return True

    def _status_bar(self) -> StatusBar:
        return self.query_one(StatusBar)

    def _top_bar(self) -> TopBar:
        return self.query_one(TopBar)

    def _slash_suggestions_panel(self) -> Static:
        return self.query_one("#slash-suggestions", Static)

    def _sidebar_status(self) -> Static:
        return self.query_one("#sidebar-status", Static)

    def _sidebar_help(self) -> Static:
        return self.query_one("#sidebar-help", Static)

    def _session_map(self) -> SessionMapWidget:
        return self.query_one("#session-map", SessionMapWidget)

    def _net_error(self, exc: Exception) -> None:
        msg = str(exc) or type(exc).__name__
        state = None
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", 0)
        if isinstance(status_code, int) and status_code:
            state = state_for_http_status(status_code)
        if state is not None:
            self._log_system(f"{state.title}. {state.explanation} {state.suggested_action}")
        else:
            self._log_system(f"Network error: {msg}")
        self._status_bar().set_connected(False)

    def _update_status(self) -> None:
        model_label = self.client.model or "no model"
        provider_label = "none"
        for item in self.models:
            if item.id == self.client.model:
                model_label = f"{item.provider}:{item.name}"
                provider_label = item.provider or "none"
                break
        if provider_label == "none" and self._runtime_store.turn.provider:
            provider_label = self._runtime_store.turn.provider
        status_width = getattr(getattr(self, "size", None), "width", 120) or 120
        self._status_bar().update_snapshot(
            StatusSnapshot(
                model=model_label,
                provider=provider_label,
                transport=self._transport_label(),
                session_id=self.session_id or "",
                queue_depth=len(self._prompt_queue),
                busy_mode=self._effective_busy_mode(),
                token_count=self._runtime_store.turn.total_tokens,
                latency_ms=self._runtime_store.turn.latency_ms,
                cost_estimate=self._runtime_store.turn.cost_estimate,
                backend_healthy=self.connected,
                agent_busy=self.streaming,
                voice_state=self._voice_state,
            ),
            width=status_width,
        )
        self._top_bar().update_model(model_label)
        self._update_sidebar()

    def _transport_label(self) -> str:
        name = type(self.transport).__name__.lower()
        if "websocket" in name:
            return "websocket"
        if "inprocess" in name or "in_process" in name:
            return "in-process"
        return "http"

    async def _complete_slash_prefix(self, prefix: str) -> list[SlashCompletionOption]:
        from keprix.tui.slash_registry import local_completion_items, slash_command_description

        local = [
            SlashCompletionOption(command=item.command, description=item.description)
            for item in local_completion_items(prefix)
        ]
        try:
            backend = await self.transport.command_complete(prefix, session_id=self.session_id or "")
        except Exception:
            backend = []
        merged: list[SlashCompletionOption] = []
        seen: set[str] = set()
        for item in [*local, *backend]:
            if isinstance(item, SlashCompletionOption):
                option = item
            else:
                command = str(item)
                option = SlashCompletionOption(command=command, description=slash_command_description(command))
            if option.command not in seen:
                merged.append(option)
                seen.add(option.command)
        return merged

    def _set_completion_hint(self, hint: str) -> None:
        self._completion_hint = hint
        self._update_status()

    def _set_completion_candidates(self, candidates: list[SlashCompletionOption], selected_index: int = 0) -> None:
        panel = self._slash_suggestions_panel()
        if not candidates:
            panel.update("")
            panel.remove_class("visible")
            return
        rows = ["Slash commands (type to filter, Up/Down or Tab, Enter selects)"]
        selected_index = max(0, min(selected_index, len(candidates) - 1))
        window_size = 12
        start = 0
        if selected_index >= window_size:
            start = selected_index - window_size + 1
        visible = candidates[start : start + window_size]
        for offset, candidate in enumerate(visible):
            index = start + offset
            marker = ">" if index == selected_index else " "
            description = f" - {candidate.description}" if candidate.description else ""
            rows.append(f"{marker} {candidate.command}{description}")
        if len(candidates) > len(visible):
            rows.append(f"{len(candidates)} matches. Keep typing to filter.")
        panel.update("\n".join(rows))
        panel.add_class("visible")

    def _update_sidebar(self) -> None:
        if not self.is_mounted:
            return
        model = self.client.model or "not selected"
        status = "online" if self.connected else "offline"
        busy = "busy" if self.streaming else "idle"
        queue_count = len(self._prompt_queue)
        session_title = "New conversation"
        for item in self.sessions:
            if item.id == self.session_id:
                session_title = item.title or "Conversation"
                break
        self._sidebar_status().update(
            "\n".join(
                [
                    f"Status: {status}",
                    f"Agent: {busy}",
                    f"Model: {model}",
                    f"Queued: {queue_count}",
                    f"Session: {session_title[:32]}",
                ]
            )
        )
        nodes = build_session_map(self.sessions, current_session_id=self.session_id, limit=4)
        self._session_map().update_map(nodes, selected_id=self.session_id)
        self._sidebar_help().update(
            "\n".join(
                [
                    "Quick actions",
                    "/new",
                    "/model",
                    "/details",
                    "/timeline",
                    "Ctrl+G editor",
                ]
            )
        )

    async def action_toggle_mouse(self) -> None:
        self._mouse_enabled = not self._mouse_enabled
        transcript = self._message_log()
        transcript.mouse_selection_enabled = self._mouse_enabled
        state = "enabled" if self._mouse_enabled else "disabled"
        self.notify(f"Mouse capture {state}.")
        self._update_status()

    def _command_center_registry(self):
        skills = [
            RegistryItem(
                name=item.name,
                description=item.description,
                installed=item.installed,
                enabled=item.enabled,
                source=item.source,
            )
            for item in self._runtime_store.skills
        ]
        plugins = [
            RegistryItem(
                name=item.name,
                description=item.description,
                version=item.version,
                installed=item.installed,
                enabled=item.enabled,
                source=item.source,
            )
            for item in self._runtime_store.plugins
        ]
        return build_default_registry(
            sessions=self.sessions,
            models=self.models,
            skills=skills,
            plugins=plugins,
            recent_files=[],
        )

    async def action_command_palette(self) -> None:
        if self._prompt_overlay_open:
            return
        self._prompt_overlay_open = True
        self._input_bar().disabled = True
        try:
            model = CommandPaletteModel(self._command_center_registry())
            action = await self.push_screen_wait(CommandPalette(model))
            if action is None:
                return
            result = dispatch_for_action(action)
            if result.dispatch_kind == "insert_text":
                inp = self._input_bar()
                inp.value = result.value
                inp.cursor_position = len(inp.value)
                return
            if result.dispatch_kind == "switch_session":
                await self.load_session(result.value)
                return
            if result.dispatch_kind == "switch_model":
                self.client.model = result.value
                self._log_system(f"Model set to {result.value}.")
                self._update_status()
                return
            if result.dispatch_kind == "switch_theme":
                theme_name = self._set_theme(result.value)
                self._log_system(f"Theme set to {theme_name}.")
                return
            if result.dispatch_kind == "runtime_action":
                if result.value == "interrupt":
                    await self.action_interrupt_turn()
                elif result.value == "flush_queue":
                    await self.action_flush_queue()
                elif result.value == "reconnect":
                    await self.action_reconnect()
                return
            if result.dispatch_kind == "open_help":
                self._log_system(self._help_text())
                return
            if result.dispatch_kind == "open_review":
                await self.action_review_mode()
                return
            if result.dispatch_kind == "open_file":
                self._log_system(f"Recent file (host/path context): {result.value}")
                return
            if result.dispatch_kind == "vault_action":
                await self._handle_vault_palette(result.value)
                return
            if result.dispatch_kind == "open_registry":
                self._log_system(f"Open {action.kind}: {result.value}")
        finally:
            self._prompt_overlay_open = False
            self._input_bar().disabled = False
            self._input_bar().focus()

    async def _handle_vault_palette(self, action_value: str) -> None:
        """Run immediate vault actions or seed /vault slash input for args."""
        immediate = {"list", "sync_status", "host_fs_note"}
        if action_value in immediate:
            await self._run_vault_command([action_value.replace("sync_status", "sync").replace("host_fs_note", "host")])
            return
        seeds = {
            "search": "/vault search ",
            "mkdir": "/vault mkdir ",
            "create_note": "/vault note ",
            "inspect": "/vault inspect ",
            "rename": "/vault rename ",
            "trash": "/vault trash ",
            "restore": "/vault restore ",
            "export": "/vault export ",
        }
        seed = seeds.get(action_value)
        if seed:
            inp = self._input_bar()
            inp.value = seed
            inp.cursor_position = len(seed)
            self._log_system("Document Vault: complete the /vault command and press Enter.")
            return
        self._log_system(f"Unknown vault action: {action_value}")

    async def _run_vault_command(self, args: list[str]) -> None:
        from keprix.tui.document_vault import DocumentVaultTuiClient, format_vault_listing

        if not args:
            self._log_system(
                "Usage: /vault list|search <q>|mkdir <name>|note <name>|inspect <id>|"
                "rename <id> <name>|trash <id>|restore <id>|export <id>|sync|host"
            )
            return
        op = args[0].lower()
        rest = args[1:]
        vault = DocumentVaultTuiClient(self.client)
        try:
            if op == "list":
                payload = await vault.list_items()
                self._log_system(format_vault_listing(payload))
                return
            if op == "search":
                query = " ".join(rest).strip()
                if not query:
                    self._log_system("Usage: /vault search <query>")
                    return
                payload = await vault.list_items(q=query)
                self._log_system(format_vault_listing(payload))
                return
            if op == "mkdir":
                name = " ".join(rest).strip() or "New folder"
                item = await vault.create_folder(name)
                self._log_system(f"Created folder: {item.get('name')} ({item.get('id')})")
                return
            if op in {"note", "create_note", "create-note"}:
                name = " ".join(rest).strip() or "Untitled"
                item = await vault.create_text(name, f"# {name}\n\n")
                self._log_system(f"Created note: {item.get('name')} ({item.get('id')})")
                return
            if op == "inspect":
                if not rest:
                    self._log_system("Usage: /vault inspect <item_id>")
                    return
                payload = await vault.read_content(rest[0])
                content = str(payload.get("content") or "")
                preview = content if len(content) <= 1200 else content[:1200] + "\n..."
                self._log_system(f"Vault item {rest[0]}:\n{preview}")
                return
            if op == "rename":
                if len(rest) < 2:
                    self._log_system("Usage: /vault rename <item_id> <new name>")
                    return
                item = await vault.rename(rest[0], " ".join(rest[1:]))
                self._log_system(f"Renamed to {item.get('name')}")
                return
            if op == "trash":
                if not rest:
                    self._log_system("Usage: /vault trash <item_id>")
                    return
                item = await vault.trash(rest[0])
                self._log_system(f"Trashed {item.get('name')}")
                return
            if op == "restore":
                if not rest:
                    self._log_system("Usage: /vault restore <item_id>")
                    return
                item = await vault.restore(rest[0])
                self._log_system(f"Restored {item.get('name')}")
                return
            if op == "export":
                if not rest:
                    self._log_system("Usage: /vault export <item_id>")
                    return
                data = await vault.export(rest[0], "md")
                self._log_system(f"Export markdown bytes={len(data)} (tenant vault; not host path)")
                return
            if op in {"sync", "sync_status"}:
                try:
                    from keprix.document_vault.google.service import GoogleDriveVaultService

                    status = GoogleDriveVaultService().status(
                        os.environ.get("KEPRIX_WORKSPACE_ID")
                        or os.environ.get("X_WORKSPACE_ID")
                        or "default"
                    )
                    connected = status.get("connected")
                    mode = status.get("mode") or "n/a"
                    last = status.get("last_sync_at") or "never"
                    err = status.get("last_error") or ""
                    webhook = "https webhook" if status.get("webhook_configured") else "local poll/manual"
                    self._log_system(
                        "Document Vault Google Drive sync\n"
                        f"connected={connected} mode={mode} last_sync={last} transport={webhook}\n"
                        f"{err or 'Local vault works without Google.'}\n"
                        "Shared Drives are gated. Use web UI /api/document-vault/google/* for connect/sync."
                    )
                except Exception as exc:
                    self._log_system(f"Document Vault sync status unavailable: {exc}")
                return
            if op == "host":
                self._log_system(
                    "Host filesystem browse is admin-only (/api/fs, desktop project tree). "
                    "It is never the tenant Document Vault."
                )
                return
            self._log_system(f"Unknown /vault operation: {op}")
        except Exception as exc:
            self._log_system(f"Document Vault error: {exc}")

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

        text = self._expand_submit_text(text)
        if not text:
            return

        if text.startswith("/"):
            command, args = parse_slash(text)
            if command == "/debug":
                self._debug_state.state = {
                    "connected": str(self.connected),
                    "streaming": str(self.streaming),
                    "session": (self.session_id or "")[:8] or "none",
                    "model": self.client.model or "",
                    "queued": str(len(self._prompt_queue)),
                    "sessions": str(len(self.sessions)),
                }
                lines = ["Debug state"]
                lines.extend(f"{key}: {value}" for key, value in sorted(self._debug_state.state.items()))
                if self._debug_state.events:
                    lines.append("")
                    lines.append("Recent events")
                    lines.extend(self._debug_state.events[-8:])
                self._log_system("\n".join(lines))
                return
            if command == "/timeline":
                result = await self._slash_timeline(args)
                if result.message:
                    self._log_system(result.message)
                return
            if command == "/open":
                url = " ".join(args).strip()
                if not url.startswith(("http://", "https://")):
                    self._log_system("Usage: /open https://example.com")
                    return
                try:
                    open_external_link(url)
                except Exception as exc:
                    self._log_system(f"Open failed: {exc}")
                    return
                self._log_system(f"Opened: {url}")
                return
            if command == "/vault":
                await self._run_vault_command(args)
                return
            if command == "/search":
                query = " ".join(args).strip()
                if not query:
                    self._log_system("Usage: /search <query>")
                    return
                from keprix.tui.message_types import TuiMessage

                messages = [
                    TuiMessage(role="system", content=item.plain_text)
                    for item in self._message_log().store.items
                ]
                matches = search_history(messages, query)
                if not matches:
                    self._log_system(f"No transcript matches for: {query}")
                    return
                lines = [f"{len(matches)} transcript matches for: {query}"]
                for match in matches[:10]:
                    lines.append(f"{match.index + 1}. {match.excerpt}")
                if len(matches) > 10:
                    lines.append(f"{len(matches) - 10} more matches. Refine the query.")
                self._log_system("\n".join(lines))
                return
            if command == "/setup":
                section = " ".join(args).strip()
                code = await self._run_setup_handoff_async(section)
                if code == 0:
                    await self._refresh_after_setup()
                    self._log_system("Setup complete.")
                else:
                    self._log_system(f"Setup exited with code {code}.")
                self._update_status()
                return
            if command == "/theme":
                requested = " ".join(args).strip()
                if not requested:
                    self._log_system("Themes: " + ", ".join(available_themes()))
                    return
                normalized = normalize_theme_name(requested)
                self._set_theme(normalized)
                self._log_system(f"Theme set to {normalized}.")
                return

        if self._setup_required:
            self._log_system("Configure a provider first (setup overlay or /setup).")
            return

        if text.startswith("/"):
            request_session = self.session_id
            result = await dispatch_slash_with_fallthrough(
                text,
                client=self.transport,
                session_id=self.session_id,
                request_session_id=request_session,
                on_quit=self.action_quit_app,
                on_model=self.action_cycle_model,
                on_clear=self.action_clear_transcript,
                on_copy=self.action_copy_last_reply,
                on_interrupt=self.action_interrupt_turn,
                on_new=self.action_new_chat,
                on_sessions=self.action_focus_sessions,
                on_reconnect=self.action_reconnect,
                on_toggle_mouse=self.action_toggle_mouse,
                queue_snapshot=self._prompt_queue.snapshot,
                get_busy_mode=self._effective_busy_mode,
                set_busy_mode=self._set_busy_mode,
                on_steer=self._slash_steer,
                on_details=self._slash_details,
                on_timeline=self._slash_timeline,
                on_voice=self._slash_voice,
            )
            if result.alias_command:
                await self._submit_text(result.alias_command)
                return
            if result.submit_text:
                if result.message:
                    self._log_system(result.message)
                await self._start_turn(result.submit_text)
                self._update_status()
                return
            if result.handled:
                if result.message:
                    if result.pager:
                        title = text.split()[0]
                        await self.push_screen_wait(PagerScreen(title, result.message))
                    else:
                        self._log_system(result.message)
                self._update_status()
                return

        self._input_history.push(text)
        self._log_user_message(text)
        if self.streaming:
            mode = self._effective_busy_mode()
            if mode == "steer":
                await self._handle_steer_submit(text)
                return
            if mode == "interrupt":
                await self._handle_interrupt_submit(text)
                return
            self._prompt_queue.enqueue(text)
            self._runtime_store.set_queue(self._prompt_queue.snapshot())
            self._set_busy(True)
            self._update_sidebar()
            self.notify(f"Queued ({len(self._prompt_queue)} waiting). Ctrl+K sends next now.")
            return
        await self._start_turn(text)

    async def _set_busy_mode(self, mode: str) -> str:
        self._local_busy_mode = mode
        save_busy_input_override(mode)
        if self.streaming:
            self._set_busy(True)
        self._update_status()
        return mode

    async def _slash_steer(self, steer_text: str) -> SlashResult:
        if not self.session_id:
            return SlashResult(handled=True, message="No active session.")
        try:
            await self.transport.steer(self.session_id, steer_text)
        except SteerNotBusyError:
            await self._start_turn(steer_text)
            return SlashResult(
                handled=True,
                message="Agent is not running. Message sent as new turn.",
            )
        except Exception as exc:
            return SlashResult(handled=True, message=f"Steer failed: {exc}")
        return SlashResult(
            handled=True,
            message=f"Steered: {steer_text}\nNote injected into current turn.",
        )

    async def _handle_steer_submit(self, text: str) -> None:
        if not self.session_id:
            return
        try:
            await self.transport.steer(self.session_id, text)
            self._log_system(f"Steered: {text}")
            self._log_system("Note injected into current turn.")
        except SteerNotBusyError:
            self._log_system("Agent is not running. Message sent as new turn.")
            await self._start_turn(text)
        except Exception as exc:
            self._log_system(f"Steer failed: {exc}")

    async def _handle_interrupt_submit(self, text: str) -> None:
        if not self.session_id:
            return
        self._pending_after_interrupt = text
        await self.action_interrupt_turn()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if not self.connected:
            self._log_system("Backend offline. Press Ctrl+Shift+R to reconnect. Press ? for help.")
            return
        if not self.session_id:
            return
        text = event.value
        event.input.value = ""
        await self._submit_text(text)

    async def _start_turn(self, text: str) -> None:
        if self._turn_task and not self._turn_task.done():
            self._prompt_queue.enqueue(text)
            return
        self._turn_task = asyncio.create_task(self._run_turn(text))
        try:
            await self._turn_task
        except asyncio.CancelledError:
            pass
        finally:
            self._turn_task = None

    async def _run_turn(self, text: str) -> None:
        thinking = self._thinking_panel()
        self.streaming = True
        self._runtime_store.start_turn(
            session_id=self.session_id or "",
            model=self.client.model or "",
        )
        self._runtime_store.timeline.add(
            RuntimeTimelineEvent(
                "transport",
                "Transport mode",
                getattr(self.transport, "mode", "unknown"),
            )
        )
        self._interrupt_requested = False
        self._set_busy(True)
        self._tool_trail = ToolTrail()
        self._subagents = SubagentList()
        self._activity_feed.clear()
        self._activity_feed.push("Turn started")
        thinking.update("")
        thinking.remove_class("visible")
        self._refresh_thinking_panel()

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
                        if kind in {
                            "file_changed",
                            "file",
                            "command_executed",
                            "command",
                            "warning",
                            "risk",
                            "test_run",
                            "test",
                            "next_action",
                            "todo",
                        }:
                            value = str(
                                payload.get("value")
                                or payload.get("path")
                                or payload.get("command")
                                or payload.get("message")
                                or payload.get("name")
                                or ""
                            )
                            self._runtime_store.record_review_item(kind, value)
                            continue
                        if kind == "text_delta":
                            assistant_parts.append(str(payload.get("content") or ""))
                            body = "".join(assistant_parts)
                            if body and not streaming_visible:
                                await self._begin_agent_stream()
                                self._runtime_store.timeline.add(
                                    RuntimeTimelineEvent("stream", "Text streaming started")
                                )
                                streaming_visible = True
                            if streaming_visible:
                                await self._update_agent_stream(body)
                            continue
                        if kind == "tool_call":
                            name = str(payload.get("name") or "tool")
                            call_id = str(payload.get("tool_call_id") or payload.get("call_id") or "")
                            args = payload.get("args") if isinstance(payload.get("args"), dict) else {}
                            self._runtime_store.start_tool(name, call_id=call_id, args=args)
                            self._tool_trail.start_tool(name)
                            self._activity_feed.push(f"Running {name}...")
                            self._refresh_thinking_panel()
                            continue
                        if kind == "tool_call_update":
                            name = str(payload.get("name") or "tool")
                            status = str(payload.get("status") or "done")
                            call_id = str(payload.get("tool_call_id") or payload.get("call_id") or "")
                            self._runtime_store.finish_tool(
                                name,
                                call_id=call_id,
                                status=status,
                                result_preview=str(payload.get("result_preview") or payload.get("preview") or ""),
                                error=str(payload.get("error") or ""),
                            )
                            self._tool_trail.finish_tool(name, status=status)
                            self._refresh_thinking_panel()
                            continue
                        if kind == "subagent_spawn":
                            sid = str(payload.get("subagent_id") or payload.get("label") or "subagent")
                            label = str(payload.get("label") or payload.get("goal") or sid)
                            self._runtime_store.spawn_subagent(
                                sid,
                                label=label,
                                parent_id=str(payload.get("parent_id") or ""),
                                preview=str(payload.get("preview") or payload.get("goal") or ""),
                            )
                            self._subagents.spawn(sid, label=label)
                            self._activity_feed.push(f"Subagent spawned: {label[:48]}")
                            self._refresh_thinking_panel()
                            continue
                        if kind == "subagent_done":
                            sid = str(payload.get("subagent_id") or payload.get("label") or "subagent")
                            label = str(payload.get("label") or payload.get("goal") or sid)
                            cost_hint = str(payload.get("cost_hint") or "")
                            self._runtime_store.finish_subagent(
                                sid,
                                label=label,
                                status=str(payload.get("status") or "done"),
                                preview=str(payload.get("preview") or payload.get("summary") or ""),
                                cost_hint=cost_hint,
                            )
                            self._subagents.complete(sid, label=label, cost_hint=cost_hint)
                            self._activity_feed.push(f"Subagent done: {label[:48]}")
                            self._refresh_thinking_panel()
                            continue
                        if kind == "activity":
                            message = str(payload.get("message") or "").strip()
                            if message:
                                self._activity_feed.push(message)
                                self._refresh_thinking_panel()
                            continue
                        if kind == "clarify":
                            self._runtime_store.timeline.add(RuntimeTimelineEvent("clarify", "Clarify requested"))
                            await self._handle_clarify_prompt(payload)
                            continue
                        if kind == "approval":
                            self._runtime_store.timeline.add(RuntimeTimelineEvent("approval", "Approval requested"))
                            await self._handle_approval_prompt(payload)
                            continue
                        if kind == "approval_resolved":
                            self._runtime_store.timeline.add(
                                RuntimeTimelineEvent("approval", "Approval resolved", status="done")
                            )
                            continue
                        if kind == "message_done":
                            message = payload.get("message") or {}
                            self._runtime_store.update_usage(payload)
                            self._runtime_store.add_message_metadata(
                                MessageRuntimeMetadata(
                                    message_id=str(message.get("id") or payload.get("message_id") or ""),
                                    role=str(message.get("role") or "assistant"),
                                    model=str(payload.get("model") or self.client.model or ""),
                                    provider=str(payload.get("provider") or ""),
                                    input_tokens=self._runtime_store.turn.input_tokens,
                                    output_tokens=self._runtime_store.turn.output_tokens,
                                    total_tokens=self._runtime_store.turn.total_tokens,
                                    latency_ms=self._runtime_store.turn.latency_ms,
                                    cost_estimate=self._runtime_store.turn.cost_estimate,
                                    tool_calls=len(self._runtime_store.tools),
                                    status="complete",
                                )
                            )
                            self._runtime_store.add_api_event(
                                ApiRuntimeEvent(
                                    request_id=str(payload.get("request_id") or ""),
                                    provider=str(payload.get("provider") or ""),
                                    model=str(payload.get("model") or self.client.model or ""),
                                    status="done",
                                    latency_ms=self._runtime_store.turn.latency_ms,
                                    input_tokens=self._runtime_store.turn.input_tokens,
                                    output_tokens=self._runtime_store.turn.output_tokens,
                                    response_preview=str(message.get("content") or "")[:500],
                                )
                            )
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
                    self.session_id = await self.transport.ensure_ready_session(None)
                    await self.refresh_sessions()
                    self._log_system(
                        "Note: previous session expired (backend may have restarted). Started a new chat."
                    )
        except asyncio.CancelledError:
            self._interrupt_requested = True
            self._runtime_store.finish_turn(status="interrupted")
            self._runtime_store.timeline.add(RuntimeTimelineEvent("interrupt", "Interrupt requested"))
            await self._end_agent_stream()
        except Exception as exc:
            self._log_system(f"Error: {exc}")
            self._runtime_store.finish_turn(status="errored")
            self._runtime_store.timeline.add(RuntimeTimelineEvent("error", "Turn errored", str(exc)[:120], "error"))
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

        self._activity_feed.clear()
        thinking.remove_class("visible")
        thinking.update("")
        self.streaming = False
        if self._runtime_store.turn.status == "running":
            self._runtime_store.finish_turn(status="interrupted" if self._interrupt_requested else "complete")
        self._set_busy(False)
        await self.refresh_sessions()

        next_text = self._pending_after_interrupt
        self._pending_after_interrupt = ""
        if next_text:
            await self._start_turn(next_text)
            return

        next_text = self._prompt_queue.pop()
        self._runtime_store.set_queue(self._prompt_queue.snapshot())
        if next_text and not self._interrupt_requested:
            await self._start_turn(next_text)

    async def _handle_clarify_prompt(self, payload: dict[str, Any]) -> None:
        if not self.session_id:
            return
        clarify_id = str(payload.get("clarify_id") or "")
        if not clarify_id:
            return
        question = str(payload.get("question") or "")
        choices_raw = payload.get("choices") or []
        choices = [str(item) for item in choices_raw] if isinstance(choices_raw, list) else []
        self._prompt_overlay_open = True
        self._input_bar().disabled = True
        try:
            overlay = ClarifyOverlay(clarify_id=clarify_id, question=question, choices=choices)
            try:
                answer = await asyncio.wait_for(
                    self.push_screen_wait(overlay),
                    timeout=float(get_tui_clarify_timeout_sec()),
                )
            except asyncio.TimeoutError:
                answer = ""
                self._log_system("Clarify dismissed.")
            else:
                if not str(answer or "").strip():
                    self._log_system("Clarify dismissed.")
            await self.client.respond_clarify(self.session_id, clarify_id, str(answer or ""))
        except Exception as exc:
            self._log_system(f"Clarify response failed: {exc}")
        finally:
            self._prompt_overlay_open = False
            self._input_bar().disabled = False
            self._input_bar().focus()

    async def _handle_approval_prompt(self, payload: dict[str, Any]) -> None:
        if not self.session_id:
            return
        approval_id = str(payload.get("approval_id") or "")
        if not approval_id:
            return
        command = str(payload.get("command") or "")
        description = str(payload.get("description") or "")
        allow_permanent = bool(payload.get("allow_permanent", True))
        self._prompt_overlay_open = True
        self._input_bar().disabled = True
        try:
            overlay = ApprovalOverlay(
                approval_id=approval_id,
                command=command,
                description=description,
                allow_permanent=allow_permanent,
            )
            decision = await self.push_screen_wait(overlay)
            if not str(decision or "").strip():
                decision = "deny"
            await self.transport.respond_approval(self.session_id, approval_id, str(decision))
        except Exception as exc:
            self._log_system(f"Approval response failed: {exc}")
        finally:
            self._prompt_overlay_open = False
            self._input_bar().disabled = False
            self._input_bar().focus()

    async def _iter_turn(self, text: str):
        if not self.session_id:
            return
        async for event in self.transport.send_message_stream(self.session_id, text):
            yield event.to_legacy_payload()

    async def action_external_editor(self) -> None:
        if self._prompt_overlay_open:
            return
        if not resolve_editor():
            self._log_system("Set EDITOR to use external compose.")
            return
        inp = self._input_bar()
        initial = inp.value
        if self._compose_lines:
            initial = "\n".join([*self._compose_lines, initial]).rstrip("\n")
        with self.suspend():
            edited = edit_in_editor(initial)
        if edited is None:
            self.notify("External editor closed without changes.")
            return
        inp.value = edited
        self._compose_lines.clear()
        inp.focus()
        self.notify("Loaded text from external editor.")

    async def action_voice_toggle(self) -> None:
        if self._prompt_overlay_open:
            return
        if not self._voice_enabled:
            self.notify("Voice input is off. Use /voice on to enable.")
            return
        if not self._voice_recorder.recording:
            try:
                self._voice_recorder.start()
            except VoiceCaptureError as exc:
                self._log_system(str(exc))
                return
            self._update_status()
            self.notify("Recording... press Ctrl+B again to stop.")
            return
        try:
            capture = self._voice_recorder.stop()
        except VoiceCaptureError as exc:
            self._log_system(str(exc))
            self._update_status()
            return
        self._update_status()
        try:
            transcript = await self.transport.transcribe_audio(
                capture.data_url,
                mime_type=capture.mime_type,
            )
        except Exception as exc:
            self._log_system(f"Transcription failed: {exc}")
            return
        if not transcript:
            self.notify("No speech detected.")
            return
        inp = self._input_bar()
        if inp.value.strip():
            inp.value = f"{inp.value.rstrip()} {transcript}"
        else:
            inp.value = transcript
        inp.focus()
        self.notify("Transcript inserted into composer.")

    async def action_interrupt_turn(self) -> None:
        if not self.streaming:
            self.notify("Nothing to interrupt.")
            return
        self._interrupt_requested = True
        if self.session_id:
            try:
                self._runtime_store.timeline.add(RuntimeTimelineEvent("interrupt", "Interrupt requested"))
                self._refresh_runtime_timeline()
                await self.transport.interrupt(self.session_id)
            except Exception:
                pass
        if self._turn_task and not self._turn_task.done():
            self._turn_task.cancel()
        self.notify("Stopping...")

    async def action_handle_ctrl_c(self) -> None:
        if self._prompt_overlay_open:
            return
        inp = self._input_bar()
        if inp.has_focus and not inp.selection.is_empty:
            inp.action_copy()
            self.notify("Input selection copied.")
            return
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
        if not self._prompt_queue:
            self.notify("Queue is empty.")
            return
        if self.streaming:
            await self.action_interrupt_turn()
            await asyncio.sleep(0)
        next_text = self._prompt_queue.pop()
        self._runtime_store.set_queue(self._prompt_queue.snapshot())
        if next_text:
            await self._start_turn(next_text)

    async def action_clear_transcript(self) -> None:
        if self.streaming:
            self.notify("Stop the current reply before clearing.")
            return
        self._message_log().clear()
        self._log_system("Transcript cleared.")

    async def action_new_chat(self) -> None:
        if self.streaming:
            self.notify("Stop the current reply first (Ctrl+C).")
            return
        try:
            session = await self.transport.create_session()
        except httpx.HTTPError as exc:
            self._net_error(exc)
            return
        await self.refresh_sessions()
        await self.load_session(session.id)
        self._update_status()

    async def action_reconnect(self) -> None:
        self._log_system("Connecting...")
        try:
            self.connected = await self.client.health_check()
        except httpx.HTTPError:
            self.connected = False
        if not self.connected:
            self._log_system("Still offline. Is keprix running? (`keprix start`)")
            self._status_bar().set_connected(False)
            self._update_sidebar()
            return
        try:
            self.models = await self.transport.list_models()
        except httpx.HTTPError as exc:
            self._net_error(exc)
            return
        if not self.client.model and self.models:
            self.client.model = self.models[0].id
        await self.refresh_sessions()
        if self.sessions:
            await self.load_session(self.sessions[0].id)
        else:
            self.session_id = await self.transport.ensure_ready_session(None)
            await self.refresh_sessions()
            await self.load_session(self.session_id)
        self._update_status()
        self._log_system("Reconnected.")

    async def action_focus_sessions(self) -> None:
        self.query_one("#session-list", ListView).focus()

    async def action_help(self) -> None:
        self._log_system(self._help_text())

    async def action_search_transcript(self) -> None:
        inp = self._input_bar()
        inp.value = "/search "
        inp.cursor_position = len(inp.value)
        inp.focus()

    async def action_cycle_model(self) -> None:
        if self._setup_required or not self.models:
            code = await self._run_setup_handoff_async("model")
            if code == 0:
                await self._refresh_after_setup()
                self.notify("Model configured.")
            else:
                self.notify("Model setup cancelled.")
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
        log = self._message_log()
        if self._mouse_enabled and log.selection.is_active:
            selected = log.selection.selected_text(log.line_map())
            if copy_text(selected):
                self.notify("Selection copied.")
            else:
                self.notify("Copy failed.")
            return
        transcript = log.store.full_plain_text()
        if copy_text(transcript):
            self.notify("Full transcript copied.")
        else:
            self.notify("Copy failed. Try Ctrl+Shift+L for the last reply only.")

    async def action_review_mode(self) -> None:
        report = build_review_report(
            self._runtime_store,
            user_request=self._last_user_text,
            assistant_outcome=self._last_agent_text,
        )
        await self.push_screen_wait(ReviewMode(report))

    async def action_focus_transcript(self) -> None:
        self._message_log().focus()

    async def action_transcript_page_up(self) -> None:
        self._message_log().scroll_page_up()

    async def action_transcript_page_down(self) -> None:
        self._message_log().scroll_page_down()

    async def action_transcript_home(self) -> None:
        self._message_log().scroll_to_top()

    async def action_transcript_end(self) -> None:
        self._message_log().scroll_to_bottom()

    async def action_transcript_first(self) -> None:
        self._message_log().scroll_to_first_message()

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
