# Keprix TUI

The Textual-based terminal UI is the Keprix Command Center. It connects to the workspace API on port `3333`, can use HTTP, WebSocket, or in-process runtime transports, and keeps the Keprix look while preserving the agent behaviors adopted from Hermes.

## Basics

- Start the backend with `keprix start`, then launch the TUI from the installed CLI.
- Sessions, models, streaming replies, clarify and approval overlays, virtual scrollback, command palette, status bar, and runtime panels are built in.
- Slash commands use local handlers first, then backend fallthrough. See [TUI slash reference](../reference/tui-slash.md).
- The left pane is the operator cockpit: sessions, runtime health, queue state, gateway state, tools, skills, plugins, and command hints.
- The main pane is the transcript, tool trail, details view, and review surface.
- The bottom pane is the composer with slash completion, busy-mode behavior, paste handling, and voice compose.

## Command Center surfaces

| Surface | Purpose |
| --- | --- |
| Workspace cockpit | Shows the active session, runtime status, model, queue count, gateway state, and high-value shortcuts |
| Session map | Lets operators inspect and switch conversation branches |
| Runtime timeline | Normalized stream of model, tool, transport, approval, and error events |
| Tool cards | Expandable tool calls with redaction and failure details |
| Details panel | Per-section visibility for thinking, tools, subagents, and activity |
| Command palette | Keyboard-first access to TUI and backend actions |
| Debug overlay | Render tree, event log, state snapshot, and diagnostics for development |
| Review mode | Copy, inspect, search, and export transcript data without losing the live session |

## First run and setup

Three surfaces share setup state via `GET /api/setup/status`:

| Surface | Role |
| --- | --- |
| `keprix setup` | Canonical full wizard (model, TTS, terminal, gateway, tools, agent) |
| TUI (`keprix tui` or `keprix --tui` when unconfigured) | One-screen provider unblock overlay |
| Web checklist | Operator hygiene only (`/api/support/onboarding/checklist`) |

Launch the Textual TUI with `keprix tui` after `keprix start`.

When no provider is configured:

- The TUI shows a **Setup required** overlay (provider, API key, optional model).
- **Enter** saves via `POST /api/setup/minimal`.
- **f** runs full setup (`keprix setup`) as a subprocess handoff.
- **d** prints the first-run docs URL.
- `/setup [section]` and `/model` (when unconfigured) also hand off to the CLI wizard.

`keprix --tui` with no provider skips the CLI exit prompt and opens the Textual TUI in setup mode (`KEPRIX_SETUP_REQUIRED=1`).

## Advanced

### Busy input modes

While the agent is working, input can interrupt (`/busy interrupt`), queue messages (`/busy queue`), or steer the current turn (`/busy steer`). Override persists locally until changed again.

### Details sections

Use `/details` to list section visibility modes:

| Section | Default | Modes |
| --- | --- | --- |
| thinking | collapsed | hidden, collapsed, expanded |
| tools | collapsed | hidden, collapsed, expanded |
| subagents | collapsed | hidden, collapsed, expanded |
| activity | hidden | hidden, collapsed, expanded |

Examples:

- `/details tools expanded` shows the full tool trail during a turn.
- `/details all collapsed` resets every section.

Configure defaults in workspace config:

```yaml
display:
  details:
    thinking: collapsed
    tools: collapsed
    subagents: collapsed
    activity: hidden
  compose_key: ctrl+g
  voice:
    enabled: true
    record_key: ctrl+b
```

### External editor compose

Press **Ctrl+G** (or the configured `display.compose_key`) to suspend the TUI and open `$EDITOR` on the current composer text. On save, trimmed text returns to the input. Set `EDITOR` or `VISUAL` if you see `Set EDITOR to use external compose.`

### Voice push-to-talk

Press **Ctrl+B** to toggle recording when voice is enabled (`/voice on`). Audio is sent to `POST /api/audio/transcribe`; the transcript is inserted into the composer without auto-send.

Optional capture backends (git or checkout; PyPI bare install not published yet):

```bash
pipx install 'keprix[tui-voice] @ git+https://github.com/malike2356/keprix.git'
# or from a local checkout:
pipx install '.[tui-voice]' --force
```

Without the extra, the TUI falls back to `arecord` or `ffmpeg` when present.

### Large paste collapse

Pastes over 2000 characters collapse to `[Pasted N lines, expanded on send]` so the composer stays responsive. The full text is restored on submit.

### Slash fallthrough

Unknown local slash commands fall through to the backend `/api/slash/exec` and `/api/command/dispatch` pipeline. User-visible failures are sanitized; raw `HTTPStatusError`, workspace identifiers, channel identifiers, and backend tracebacks must not be printed into the transcript.

## Hermes parity matrix

| Feature | Hermes TUI | Keprix TUI |
| --- | --- | --- |
| Session list + streaming chat | Yes | Yes |
| Busy modes (interrupt/queue/steer) | Yes | Yes |
| Clarify / approval overlays | Yes | Yes |
| Virtual scrollback + selection copy | Yes | Yes |
| Slash fallthrough + tab completion | Yes | Yes |
| Details sections (tools/subagents) | Yes | Yes |
| Activity feed (8 lines) | Yes | Yes |
| External `$EDITOR` compose | Yes | Yes |
| Push-to-talk voice | Yes | Yes (optional deps) |
| Large paste collapse | Yes | Yes |
| Setup required overlay + handoff | Yes | Yes |
| Details panel and API inspector | Yes | Yes |
| Resize handler and graceful reflow | Yes | Yes |
| Debug overlay | Yes | Yes |
| External link opening | Yes | Yes |
| Runtime timeline | Partial | Yes |
| Tool cards | Partial | Yes |
| Session map | Yes | Yes |
| Command Center cockpit | No | Yes |
| Theme and skin system | Yes | Yes |

The current parity target is full behavioral parity without copying Hermes look and feel. Keprix keeps its own layout, visual language, and product extensions.

## Validation

Use the TUI checks after changing runtime, renderer, command, or theme code:

```bash
# Prefer project venv Python 3.11+
.venv/bin/python -m pytest tests/tui -q
bash scripts/check-tui-parity.sh
bash scripts/check-tui-surpass-hermes.sh
bash scripts/check-agent-parity.sh
bash scripts/check-private-ship-gate.sh
```

`check-tui-parity.sh` proves the 100/100 Hermes behavior contract.
`check-tui-surpass-hermes.sh` proves Keprix Command Center and superiority
contracts on top of parity. `check-agent-parity.sh` covers agent runtime
alignment. `check-private-ship-gate.sh` bundles those gates with architecture,
auth, billing, and frontend typecheck for private soft ship.

As of 2026-07-27, the TUI suite covers slash commands, command palette,
renderer contracts, runtime transports, keyboard behavior, terminal
capability detection, theme contrast, fault recovery, review mode, tool
cards, session map, and the Command Center proof contracts.

## Optional dependencies

Install from GitHub or a local checkout (PyPI package `keprix` is not published yet):

```bash
pipx install 'keprix[tui] @ git+https://github.com/malike2356/keprix.git'          # Textual UI
pipx install 'keprix[tui-voice] @ git+https://github.com/malike2356/keprix.git'    # sounddevice + numpy capture
# or from a checkout:
# pipx install '.[tui]' --force
# pipx install '.[tui-voice]' --force
```

See [install.md](../getting-started/install.md) and [pypi-publish-checklist.md](../operations/pypi-publish-checklist.md).
