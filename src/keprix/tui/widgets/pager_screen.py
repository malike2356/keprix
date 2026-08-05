"""Modal pager for long slash command output."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, RichLog, Static


class PagerScreen(ModalScreen[None]):
    """Scrollable pager for slash output (j/k/g/G/Space/q)."""

    BINDINGS = [
        Binding("q", "close", "Close"),
        Binding("escape", "close", "Close"),
        Binding("j", "scroll_down", "Down"),
        Binding("k", "scroll_up", "Up"),
        Binding("g", "scroll_home", "Top"),
        Binding("G", "scroll_end", "Bottom"),
        Binding("space", "page_down", "Page down"),
    ]

    DEFAULT_CSS = """
    PagerScreen {
        align: center middle;
    }

    #pager-frame {
        width: 95%;
        height: 90%;
        background: #001A00;
        border: solid #003B00;
        padding: 1 1;
        color: #00FF41;
    }

    #pager-log {
        height: 1fr;
        background: #000000;
        color: #00CC33;
    }
    """

    def __init__(self, title: str, body: str) -> None:
        super().__init__()
        self._title = title
        self._body = body

    def compose(self) -> ComposeResult:
        with Vertical(id="pager-frame"):
            yield Static(self._title, id="pager-title")
            yield RichLog(id="pager-log", wrap=True, highlight=False, markup=False)
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#pager-log", RichLog)
        for line in self._body.splitlines() or [""]:
            log.write(line)

    def _log(self) -> RichLog:
        return self.query_one("#pager-log", RichLog)

    def action_scroll_down(self) -> None:
        self._log().scroll_down()

    def action_scroll_up(self) -> None:
        self._log().scroll_up()

    def action_scroll_home(self) -> None:
        self._log().scroll_home()

    def action_scroll_end(self) -> None:
        self._log().scroll_end()

    def action_page_down(self) -> None:
        self._log().scroll_page_down()

    def action_close(self) -> None:
        self.dismiss(None)
