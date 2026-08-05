"""Virtualized transcript widget for long TUI sessions."""

from __future__ import annotations

from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.events import MouseDown, MouseMove, MouseUp
from textual.reactive import reactive
from textual.widgets import Static

from keprix.tui.clipboard import copy_text
from keprix.tui.selection import (
    TranscriptLineMap,
    TranscriptSelection,
    copy_on_select_enabled,
    render_item_with_selection,
)
from keprix.tui.transcript_store import (
    TranscriptItem,
    TranscriptStore,
    item_from_transcript_line,
    virtual_overscan,
    virtual_window_size,
)


class _HeightSpacer(Static):
    """Invisible spacer preserving scroll range for unmounted rows."""

    DEFAULT_CSS = """
    _HeightSpacer {
        width: 1fr;
        height: auto;
        opacity: 0;
    }
    """


class _TranscriptRow(Static):
    """One transcript message row."""

    DEFAULT_CSS = """
    _TranscriptRow {
        width: 1fr;
        height: auto;
    }
    """


class VirtualTranscript(VerticalScroll):
    """Windowed transcript view backed by TranscriptStore."""

    can_focus = True

    BINDINGS = [
        Binding("shift+left", "selection_left", "Select left", show=False),
        Binding("shift+right", "selection_right", "Select right", show=False),
        Binding("shift+up", "selection_up", "Select up", show=False),
        Binding("shift+down", "selection_down", "Select down", show=False),
    ]

    DEFAULT_CSS = """
    VirtualTranscript {
        height: 1fr;
        background: #000000;
        padding: 1 2;
        color: #00FF41;
    }

    #transcript-body {
        width: 1fr;
        height: auto;
    }
    """

    at_bottom: reactive[bool] = reactive(True)

    def __init__(
        self,
        *,
        store: TranscriptStore | None = None,
        mouse_selection_enabled: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.store = store or TranscriptStore()
        self.mouse_selection_enabled = mouse_selection_enabled
        self.selection = TranscriptSelection()
        self._batch_depth = 0
        self._mount_start = -1
        self._mount_end = -1
        self._sticky_follow = True
        self._refreshing = False
        self._dragging = False
        self._line_map_cache: TranscriptLineMap | None = None

    def compose(self):
        with Vertical(id="transcript-body"):
            yield _HeightSpacer(id="top-spacer")
            yield Vertical(id="transcript-rows")
            yield _HeightSpacer(id="bottom-spacer")

    def begin_batch(self) -> None:
        self._batch_depth += 1

    def end_batch(self) -> None:
        if self._batch_depth > 0:
            self._batch_depth -= 1
        if self._batch_depth == 0:
            self._refresh_window(scroll_to_bottom=True)

    def line_map(self) -> TranscriptLineMap:
        self._line_map_cache = TranscriptLineMap.from_store(self.store)
        return self._line_map_cache

    def clear(self) -> None:
        self.store.clear()
        self.selection.clear()
        self._line_map_cache = None
        self._mount_start = -1
        self._mount_end = -1
        if self.is_mounted:
            rows = self.query_one("#transcript-rows", Vertical)
            rows.remove_children()
            self._update_spacers(0, -1)
            self.scroll_to(y=0, animate=False)
        self.at_bottom = True

    def append_item(self, item: TranscriptItem) -> None:
        was_at_bottom = self.at_bottom or self._sticky_follow
        self.store.append(item)
        self._line_map_cache = None
        if self._batch_depth:
            return
        self._refresh_window(scroll_to_bottom=was_at_bottom)

    def append_line(self, line: str) -> None:
        item = item_from_transcript_line(line)
        if item is None:
            return
        self.append_item(item)

    def append_system(self, line: str) -> None:
        cleaned = line.strip()
        if not cleaned:
            return
        item = TranscriptItem.create(role="system", plain_text=cleaned, body=cleaned)
        self.append_item(item)

    def append_user(self, body: str) -> None:
        text = body.strip()
        if not text:
            return
        item = TranscriptItem.create(role="user", plain_text=f"You: {text}", body=text)
        self.append_item(item)

    def append_agent(self, body: str) -> None:
        text = body.strip()
        if not text:
            return
        item = TranscriptItem.create(role="agent", plain_text=f"keprix: {text}", body=text)
        self.append_item(item)

    def scroll_to_bottom(self, *, animate: bool = False) -> None:
        self._sticky_follow = True
        self.scroll_end(animate=animate)
        self.at_bottom = True

    def scroll_to_top(self, *, animate: bool = False) -> None:
        self._sticky_follow = False
        self.scroll_home(animate=animate)
        self.at_bottom = False

    def scroll_page_up(self) -> None:
        self._sticky_follow = False
        height = max(1, self.size.height // 2)
        self.scroll_to(y=max(0, self.scroll_y - height), animate=False)
        self._sync_at_bottom()

    def scroll_page_down(self) -> None:
        height = max(1, self.size.height // 2)
        self.scroll_to(y=min(self.max_scroll_y, self.scroll_y + height), animate=False)
        self._sync_at_bottom()

    def scroll_to_first_message(self) -> None:
        self.scroll_to_top(animate=False)
        if self.store.items:
            self.append_system("Jumped to first message.")

    def _sync_at_bottom(self) -> None:
        self.at_bottom = self.scroll_y >= self.max_scroll_y

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        if old_value == new_value or self._refreshing or not self.is_mounted:
            return
        self._sync_at_bottom()
        self._sticky_follow = self.at_bottom
        self.call_after_refresh(lambda: self._refresh_window(scroll_to_bottom=False))

    def on_mount(self) -> None:
        self.call_after_refresh(lambda: self._refresh_window(scroll_to_bottom=True))

    def _refresh_window(self, *, scroll_to_bottom: bool) -> None:
        if not self.is_mounted or self._refreshing:
            return
        self._refreshing = True
        try:
            viewport = max(1, self.size.height)
            scroll_y = int(self.scroll_y)
            start, end = self.store.mount_index_range(
                scroll_y,
                viewport,
                max_window=virtual_window_size(),
                overscan=virtual_overscan(),
            )
            if start == self._mount_start and end == self._mount_end and not scroll_to_bottom:
                self._update_spacers(start, end)
                return
            self._mount_start = start
            self._mount_end = end
            rows = self.query_one("#transcript-rows", Vertical)
            rows.remove_children()
            if end >= start >= 0:
                line_map = self.line_map()
                mounted = [
                    _TranscriptRow(
                        render_item_with_selection(
                            self.store.items[index],
                            index,
                            line_map,
                            self.selection,
                        )
                    )
                    for index in range(start, end + 1)
                ]
                rows.mount_all(mounted)
            self._update_spacers(start, end)
            if scroll_to_bottom:
                self.call_after_refresh(self.scroll_to_bottom)
        finally:
            self._refreshing = False

    def _update_spacers(self, start: int, end: int) -> None:
        if not self.is_mounted:
            return
        top = self.query_one("#top-spacer", _HeightSpacer)
        bottom = self.query_one("#bottom-spacer", _HeightSpacer)
        if start > 0 and start < len(self.store.prefix_heights):
            top_height = self.store.prefix_heights[start]
        else:
            top_height = 0
        if end >= 0 and end < len(self.store.items) - 1:
            bottom_start = self.store.prefix_heights[end + 1]
            bottom_height = max(0, self.store.total_height - bottom_start)
        else:
            bottom_height = 0
        top.styles.height = top_height
        bottom.styles.height = bottom_height

    @property
    def mounted_row_count(self) -> int:
        if self._mount_end < self._mount_start:
            return 0
        return self._mount_end - self._mount_start + 1

    def _cell_at_event(self, event_y: float, event_x: float) -> tuple[int, int]:
        return self.selection.cell_at(
            local_y=event_y,
            local_x=event_x,
            scroll_y=int(self.scroll_y),
            line_map=self.line_map(),
        )

    def on_mouse_down(self, event: MouseDown) -> None:
        if not self.mouse_selection_enabled:
            return
        self.focus()
        row, col = self._cell_at_event(event.y, event.x)
        self.selection.start_at(row, col, extend=event.shift)
        self._dragging = True
        self._refresh_window(scroll_to_bottom=False)
        event.stop()

    def on_mouse_move(self, event: MouseMove) -> None:
        if not self.mouse_selection_enabled or not self._dragging:
            return
        row, col = self._cell_at_event(event.y, event.x)
        self.selection.extend_to(row, col)
        self._refresh_window(scroll_to_bottom=False)
        event.stop()

    def on_mouse_up(self, event: MouseUp) -> None:
        if not self.mouse_selection_enabled or not self._dragging:
            return
        self._dragging = False
        if copy_on_select_enabled() and self.selection.is_active:
            selected = self.selection.selected_text(self.line_map())
            if copy_text(selected):
                self.notify("Selection copied.")
        event.stop()

    def action_selection_left(self) -> None:
        self._ensure_selection_origin()
        self.selection.extend_by_arrow(0, -1, self.line_map())
        self._refresh_window(scroll_to_bottom=False)

    def action_selection_right(self) -> None:
        self._ensure_selection_origin()
        self.selection.extend_by_arrow(0, 1, self.line_map())
        self._refresh_window(scroll_to_bottom=False)

    def action_selection_up(self) -> None:
        self._ensure_selection_origin()
        self.selection.extend_by_arrow(-1, 0, self.line_map())
        self._refresh_window(scroll_to_bottom=False)

    def action_selection_down(self) -> None:
        self._ensure_selection_origin()
        self.selection.extend_by_arrow(1, 0, self.line_map())
        self._refresh_window(scroll_to_bottom=False)

    def _ensure_selection_origin(self) -> None:
        if self.selection.anchor is not None:
            return
        line_map = self.line_map()
        if not line_map.lines:
            return
        row = min(len(line_map.lines) - 1, int(self.scroll_y) + max(0, self.size.height // 2))
        self.selection.start_at(row, 0)
