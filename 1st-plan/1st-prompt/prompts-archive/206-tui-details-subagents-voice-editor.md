# Keprix Prompt 206: TUI Details Panels, Subagents, Voice, and External Editor

## Purpose

Close the remaining Hermes TUI functional gap: **collapsible thinking/tools/subagent
sections**, `/details` visibility modes, **push-to-talk voice**, and **$EDITOR compose**.
All behavior ports; keep existing green Textual chrome.

Depends on **201** (turn control), **202** (overlays pattern), **205** (slash `/details`).

---

## Hermes reference

| File | What to port |
| --- | --- |
| `ui-tui/src/domain/details.ts` | `sectionMode()`, hidden/collapsed/expanded |
| `ui-tui/src/components/thinking.tsx` | `ToolTrail`, subagent sparkline |
| `ui-tui/src/lib/subagentTree.ts` | Nested spawn tree |
| `ui-tui/src/components/todoPanel.tsx` | In-turn todos |
| `ui-tui/src/app/useComposerState.ts` | `openEditor()`, paste collapse |
| `ui-tui/src/app/useInputHandlers.ts` | `voiceRecordToggle()` |
| `ui-tui/src/app/slash/commands/core.ts` | `/details`, `/voice` |

---

## Dependencies

- `src/keprix/tui/app.py`
- Stream events: `tool_call`, `tool_call_update`, `subagent_*` (add if missing)
- `docs/features/web-voice-input.md` (STT API on :3333)
- Prompt **188-192** web voice stack (reuse `/api/audio/transcribe`)

---

## Part A: Details sections (`/details`)

### Config

Read from config snapshot:

```yaml
display:
  details:
    thinking: collapsed   # hidden | collapsed | expanded
    tools: collapsed
    subagents: collapsed
    activity: hidden
```

### TUI state

`src/keprix/tui/details.py`:

```python
Section = Literal["thinking", "tools", "subagents", "activity"]
def cycle_mode(current: str) -> str: ...  # hidden -> collapsed -> expanded -> hidden
```

### Slash

- `/details` list modes
- `/details tools expanded` set one section
- `/details all collapsed` reset

### Rendering (reuse `#thinking-panel`, extend)

Replace flat thinking lines with structured **ToolTrail**:

```
[tools] 2 running, 1 done
  done    web_search
  run     terminal (12s)
```

- Collapsed: one summary line
- Expanded: all steps with status + duration
- Hidden: omit section entirely

Subagent tree (when stream events include `subagent_spawn`, `subagent_done`):

```
[subagents]
  coder-1  running  refactor auth/
  coder-2  done     (+$0.02, 45s)
```

Add NDJSON events in backend if not present (grep `subagent` in gateway stream).

---

## Part B: Activity feed

Transient status lines (max 8) in dim system style:

- `Indexing memory...`
- `Prefetching Honcho context...`

Port `turnController.pushActivity()` as `ActivityFeed` deque in app, cleared on turn end.

---

## Part C: External editor compose

### Behavior

- Binding: `Ctrl+G` (configurable `display.compose_key`)
- Suspend Textual (`app.suspend()`), spawn `$EDITOR` on temp file with current composer text
- On exit, load file into input; strip trailing newlines

### Implementation

`src/keprix/tui/external_editor.py`:

```python
def edit_in_editor(initial: str, *, editor: str | None = None) -> str | None: ...
```

Handle missing `$EDITOR` with system message `Set EDITOR to use external compose.`

Hermes reference: `useComposerState.openEditor()`.

---

## Part D: Voice push-to-talk

### Backend

Reuse `POST /api/audio/transcribe` (prompt 188). Send multipart wav/webm from TUI.

### TUI

`src/keprix/tui/voice.py`:

- Optional dependency: `sounddevice` + `numpy` OR invoke `arecord` / `ffmpeg` subprocess
  (document in `pyproject.toml` optional `tui-voice` extra)
- Binding: `Ctrl+B` toggle record (match `voice.record_key` config if set)
- Status bar: `REC` indicator (text only, no red dot emoji; use `[REC]` prefix)

Flow:

1. Start recording on key down (or toggle)
2. Stop on second press or max 120s
3. POST audio, insert transcript into composer (do not auto-send)
4. `/voice on|off` slash sets enabled flag

---

## Part E: Large paste collapse (composer)

When paste > 2000 chars:

- Replace composer content with `[Pasted N lines, expanded on send]`
- Store snip in `_paste_snips` dict
- On submit, expand before send

Port `handleResolvedPaste` from Hermes `useComposerState.ts`.

---

## Tests

```
tests/tui/test_details.py
tests/tui/test_external_editor.py
tests/tui/test_voice.py              # mock transcribe API
tests/tui/test_paste_snip.py
tests/api/test_stream_subagent_events.py  # if events added
```

---

## Acceptance criteria

- [ ] `/details tools expanded` shows full tool trail during turn
- [ ] Subagent spawn visible when delegate_task runs (at least flat list)
- [ ] Ctrl+G opens editor and returns text to composer
- [ ] Ctrl+B records and transcribes when `tui-voice` extra installed; honest error otherwise
- [ ] Large paste does not freeze TUI
- [ ] Activity feed shows at most 8 lines, clears on turn end
- [ ] No new color palette; sections use existing thinking panel styles

---

## Out of scope

- Full spawn tree `/replay` archive (Hermes advanced)
- Skin/theme sync from gateway
- FPS / perf debug pane

---

## Documentation

Add `docs/features/tui.md` section **Advanced** listing:

- Busy modes, details, voice, editor, slash fallthrough
- Optional deps: `pip install 'keprix[tui-voice]'`
- Hermes parity matrix (table: feature vs status)

Update `mkdocs.yml` nav if `tui.md` is new.
