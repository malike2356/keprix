# Keprix Prompt 203: TUI Virtual Scrollback for Long Sessions

## Purpose

`RichLog` mounts every line; long sessions slow down and memory grows. Port Hermes
**virtual history** behavior: windowed rendering with height cache and sticky tail follow.

No visual redesign; same message blocks, only performance and scroll behavior change.

---

## Hermes reference

| File | What to port |
| --- | --- |
| `ui-tui/src/hooks/useVirtualHistory.ts` | Window mount, offset cache, sticky follow |
| `ui-tui/src/app/scroll.ts` | `scrollBoundsForDelta`, selection-aware scroll |
| `ui-tui/src/lib/wheelAccel.ts` | Trackpad acceleration (optional) |
| `ui-tui/src/__tests__/virtualHistory*.test.ts` | Clamp and offset tests |

---

## Dependencies

- `src/keprix/tui/app.py`
- Textual `RichLog` or replace with custom `VirtualTranscript` widget

---

## Design

### Data model

```python
@dataclass
class TranscriptItem:
    id: str
    role: Literal["user", "agent", "system"]
    plain_text: str          # for copy/search
    renderable: RenderableType | None  # Rich Markdown for agent
    estimated_height: int    # rows, refined after mount
```

Store full history in `TranscriptStore` (list, max optional cap e.g. 5000 items with
archive warning).

### Virtual window

Constants (env-tunable):

- `KEPRIX_TUI_VIRTUAL_WINDOW=120` max mounted items
- `KEPRIX_TUI_VIRTUAL_OVERSCAN=8` items above/below viewport

Algorithm:

1. On scroll position change, compute first/last visible index from cumulative heights.
2. Mount only items in `[start - overscan, end + overscan]`.
3. Cache `prefix_height[i]` incrementally; invalidate from changed index on new message.
4. **Sticky tail**: if user was at bottom before new delta, auto-scroll to bottom.

### Widget

Create `src/keprix/tui/widgets/virtual_transcript.py`:

- Subclass `VerticalScroll` + internal container for mounted rows
- Each row: existing `_log_user_message` / `_log_agent_message` renderables as child `Static`
  or small `RichLog` per message (pick one; prefer single Static with Rich renderable)
- API: `append(item)`, `clear()`, `scroll_to_bottom()`, `property at_bottom`

Replace `#message-log` RichLog in `app.py` or wrap RichLog for backward compat during migration.

### Streaming row

During active stream, keep **one live row** outside virtual window logic or pin as last item
with `pinned=True` so it always mounts.

---

## Keybindings (functional)

| Key | Action |
| --- | --- |
| PageUp / PageDown | Half viewport scroll (Hermes) |
| Home / End | Top / bottom of transcript |
| Ctrl+Home | Jump to first message (log system note) |

Mouse wheel: default Textual scroll; optional acceleration behind `KEPRIX_TUI_WHEEL_ACCEL=1`.

---

## Copy integration

`action_copy_transcript` reads from `TranscriptStore.plain_text` full history, not mounted
widgets only.

---

## Tests

```
tests/tui/test_virtual_transcript.py
tests/tui/test_transcript_store.py
```

Unit tests (no Textual pilot required):

- Windowing: 1000 items, only ~120 mounted
- Sticky tail: new append while at bottom increments scroll offset
- Height cache reuse after append
- `prefix_height` monotonic

Optional pilot test: append 200 messages, assert DOM node count bounded.

---

## Acceptance criteria

- [ ] Session with 500+ messages remains responsive (scroll < 100ms perceived)
- [ ] Memory stable when scrolling full history
- [ ] Visual output identical to pre-203 for same messages (snapshot test optional)
- [ ] Copy all / copy last reply still correct
- [ ] Load session from API populates store without mounting all at once (batch render)

---

## Out of scope

- Full-text search UI (future `/search` slash)
- Persisted scroll position across TUI restarts
