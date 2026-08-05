from __future__ import annotations

from keprix.tui.renderer.diff import RenderFrame, diff_frames, diff_render_frames


def test_noop_frame_diff_has_no_dirty_rows() -> None:
    diff = diff_frames(["a", "b"], ["a", "b"])
    assert diff.changed is False
    assert diff.dirty_row_count == 0
    assert diff.dirty_ranges == ()


def test_dirty_rows_and_cell_ranges_are_detected() -> None:
    diff = diff_frames(["alpha", "bravo"], ["alpha", "braxo", "charlie"])
    assert diff.changed_lines == (1, 2)
    assert diff.dirty_ranges[0].row == 1
    assert diff.dirty_ranges[0].start == 3
    assert diff.dirty_ranges[0].end == 4
    assert "dirty_rows" in diff.debug_snapshot()


def test_cursor_changes_do_not_force_dirty_rows() -> None:
    before = RenderFrame.from_lines(["same"], cursor=(0, 1))
    after = RenderFrame.from_lines(["same"], cursor=(0, 2))
    diff = diff_render_frames(before, after)
    assert diff.changed is True
    assert diff.changed_lines == ()
    assert diff.cursor_changed is True
