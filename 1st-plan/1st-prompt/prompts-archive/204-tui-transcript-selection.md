# Keprix Prompt 204: TUI Transcript Text Selection and Copy

## Purpose

Keyboard copy shortcuts exist, but users expect **mouse drag selection** and **shift+arrow
selection** like Hermes Ink. Implement transcript selection in Textual without changing
the green theme or layout.

---

## Hermes reference

| File | What to port |
| --- | --- |
| `packages/hermes-ink/src/ink/hooks/use-selection.ts` | Selection range, drag, shift+arrows |
| `packages/hermes-ink/src/ink/selection.ts` | Coordinate mapping |
| `ui-tui/src/app/useInputHandlers.ts` | `copySelection()`, platform copy shortcut |
| `packages/hermes-ink/src/ink/termio/osc.ts` | OSC 52 clipboard |
| `ui-tui/src/app/scroll.ts` | `scrollWithSelectionBy` |

Keprix baseline: `clipboard.py` (xclip, wl-copy, OSC 52), `--mouse` flag in `cli.py`.

---

## Dependencies

- Prompt **203** recommended (virtual transcript rows expose stable line mapping)
- `src/keprix/tui/app.py`, `theme.tcss`

---

## Approach options (pick in implementation)

### Option A: Textual native selection (preferred if viable)

Investigate Textual 1.x `RichLog` / `Static` selection APIs and `Screen.get_selection()`.
If sufficient, wire mouse drag + shift+arrows to copy via `clipboard.copy_text`.

### Option B: Custom selection layer (Hermes port)

Create `src/keprix/tui/selection.py`:

```python
@dataclass
class SelectionRange:
    start: tuple[int, int]  # row, col in transcript coordinates
    end: tuple[int, int]

class TranscriptSelection:
    def cell_at(self, x: int, y: int) -> tuple[int, int]: ...
    def extend(self, row: int, col: int) -> None: ...
    def selected_text(self, store: TranscriptStore) -> str: ...
```

Wire in `app.py`:

- `on_mouse_down`, `on_mouse_up`, `on_mouse_move` when focus region is transcript
- Shift+arrow keys when transcript focused (new binding `focus_transcript`: Ctrl+Shift+T)
- Visual: invert or underline selected range using Rich `Style(reverse=True)` on re-render
  (functional highlight; keep green foreground, do not add new theme colors)

### Mouse policy

| CLI flag | Mouse | Selection |
| --- | --- | --- |
| default (`mouse=False`) | Off | Terminal native selection (shift+drag) |
| `--mouse` | On | In-TUI selection layer (this prompt) |

Document in `--help` epilog.

---

## Copy shortcuts (unify with Hermes)

| Shortcut | Action |
| --- | --- |
| Ctrl+Shift+C | Copy selection if active, else full transcript |
| Ctrl+Shift+L | Last agent reply (unchanged) |
| Ctrl+Insert / Shift+Insert | Copy / paste on Windows terminals (if detectable) |

Platform-aware: on macOS Terminal, prefer Cmd+C when transcript focused (detect
`TERM_PROGRAM`).

### Copy-on-select (optional, env flag)

`KEPRIX_TUI_COPY_ON_SELECT=1` copies on mouse release (iTerm2 style). Default off.

---

## Composer selection

Port Hermes `textInput.tsx` behavior for `#input-bar`:

- Double-click word select
- Ctrl+A select all in input
- Ctrl+C copy input selection (does not quit when input has selection; refine prompt 201
  Ctrl+C precedence: selection > interrupt > clear > quit)

Use Textual `Input` selection if available; else defer composer selection to follow-up.

---

## Tests

```
tests/tui/test_selection.py
tests/tui/test_clipboard_osc52.py
```

- `TranscriptSelection.selected_text` across user + agent messages
- Empty selection returns False from copy
- OSC 52 path invoked when no xclip/wl-copy (mock stdout)

---

## Acceptance criteria

- [ ] With `--mouse`, user can drag-select agent reply text and Ctrl+Shift+C copies it
- [ ] Selection survives scroll when using virtual transcript (203)
- [ ] Without `--mouse`, shift+drag still works via terminal (no regression)
- [ ] Copy includes plain text without Rich markup artifacts
- [ ] No theme color changes

---

## Out of scope

- Hyperlink click to open browser (separate small prompt)
- Image copy
