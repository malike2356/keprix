"""Tests for keprix TUI viewport and cursor tracking."""

from keprix.tui.viewport import ViewportState
from keprix.tui.cursor import CursorState, _char_width, cursor_diff


class TestViewport:
    def test_initial_state(self):
        vp = ViewportState()
        assert vp.scroll_offset == 0
        assert vp.auto_scroll is True
        assert vp.at_bottom is True

    def test_scroll_down(self):
        vp = ViewportState(viewport_height=10, content_height=100)
        vp.scroll_down(5)
        assert vp.scroll_offset == 5
        assert vp.at_bottom is False

    def test_scroll_down_clamped(self):
        vp = ViewportState(viewport_height=10, content_height=20)
        vp.scroll_down(20)
        assert vp.scroll_offset == 10
        assert vp.at_bottom is True

    def test_scroll_up_disables_auto_scroll(self):
        vp = ViewportState(viewport_height=10, content_height=100, scroll_offset=50)
        vp.scroll_up(10)
        assert vp.scroll_offset == 40
        assert vp.at_bottom is False
        assert vp.auto_scroll is False

    def test_scroll_to_bottom_re_enables_auto_scroll(self):
        vp = ViewportState(viewport_height=10, content_height=100, scroll_offset=50, auto_scroll=False)
        vp.scroll_to_bottom()
        assert vp.scroll_offset == 90
        assert vp.at_bottom is True
        assert vp.auto_scroll is True

    def test_toggle_auto_scroll(self):
        vp = ViewportState(viewport_height=10, content_height=100, scroll_offset=50, auto_scroll=True)
        new_state = vp.toggle_auto_scroll()
        assert new_state is False
        new_state = vp.toggle_auto_scroll()
        assert new_state is True
        assert vp.at_bottom is True

    def test_visible_range(self):
        vp = ViewportState(viewport_height=10, content_height=100, scroll_offset=25)
        first, last = vp.visible_range()
        assert first == 25
        assert last == 35

    def test_is_line_visible(self):
        vp = ViewportState(viewport_height=10, content_height=100, scroll_offset=50)
        assert vp.is_line_visible(50) is True
        assert vp.is_line_visible(59) is True
        assert vp.is_line_visible(49) is False
        assert vp.is_line_visible(60) is False

    def test_resize_preserves_bottom(self):
        vp = ViewportState(viewport_height=20, content_height=100, scroll_offset=80)
        vp.update_dimensions(viewport_height=10, content_height=100)
        assert vp.scroll_offset == 90
        assert vp.at_bottom is True

    def test_anchor_to_message(self):
        vp = ViewportState(viewport_height=10, content_height=100, scroll_offset=50)
        vp.anchor_to_message(55)
        assert vp.anchor_message_index == 55


class TestCursor:
    def test_cursor_advance(self):
        c = CursorState(x=0, y=0, max_width=80)
        c.advance(5)
        assert c.x == 5
        assert c.y == 0

    def test_cursor_wrap(self):
        c = CursorState(x=78, y=0, max_width=80)
        c.advance(5)
        assert c.x == 3
        assert c.y == 1

    def test_cursor_advance_text(self):
        c = CursorState(x=0, y=0, max_width=80)
        c.advance_text("Hello\nWorld")
        assert c.x == 5
        assert c.y == 1

    def test_cursor_clone(self):
        c = CursorState(x=10, y=5, max_width=80)
        clone = c.clone()
        clone.advance(5)
        assert c.x == 10  # original unchanged
        assert clone.x == 15

    def test_char_width(self):
        assert _char_width("a") == 1
        assert _char_width(" ") == 1
        assert _char_width("\t") == 1
        # CJK character
        assert _char_width("\u4e2d") == 2  # 中
        # Zero-width
        assert _char_width("\u200b") == 0
        # Combining accent
        assert _char_width("\u0301") == 0

    def test_cursor_diff(self):
        old = CursorState(x=0, y=0, max_width=80)
        new = CursorState(x=10, y=2, max_width=80)
        diff = cursor_diff(old, new)
        assert "\033[2B" in diff  # down 2
        assert "\033[11G" in diff  # column 11 (x=10, 1-indexed)
