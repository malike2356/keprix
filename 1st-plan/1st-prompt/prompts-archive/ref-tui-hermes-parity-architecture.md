# TUI Hermes parity architecture reference

Last updated: 2026-07-06

## Purpose

Map Hermes Agent Ink TUI functional behaviors to Keprix Textual TUI implementation
targets. Visual styling stays in `src/keprix/tui/styles/theme.tcss`; this document
covers behavior only.

## Current Keprix TUI baseline

| Area | Location | Status |
| --- | --- | --- |
| HTTP client + NDJSON stream | `src/keprix/tui/client.py` | Shipped |
| Textual app shell | `src/keprix/tui/app.py` | Shipped (MVP+) |
| Queue + interrupt + slash subset | `composer.py`, `slash_commands.py` | Shipped |
| Streaming markdown | `Markdown` + `MarkdownStream` | Shipped |
| Clipboard helpers | `clipboard.py` | Shipped |

Hermes reference tree (read-only):

`planning/competitor-research/agents-to-adopt/hermes-agent/ui-tui/`

## Build order (prompts 201-206)

```text
201 Steer + busy_input_mode
  |
  v
202 Approval + clarify overlays (needs live turn control)
  |
  +--> 203 Virtual scrollback (independent)
  |
  +--> 204 Transcript selection (independent)
  |
  v
205 Slash gateway fallthrough + tab completion
  |
  v
206 Details panels, subagents, voice, external editor
```

## Transport gap

Hermes TUI talks to a **gateway WebSocket RPC** (`session.steer`, `session.interrupt`,
`slash.exec`, `clarify.respond`). Keprix TUI uses **HTTP** to `POST /api/conversations/{id}/messages`.

Prompts 201-202 must add HTTP control-plane endpoints (or a TUI WebSocket) that wrap the
existing in-process agent hooks (`agent._pending_steer`, `clarify_callback`,
approval gateways). Do not fork a second agent runtime for the TUI.

## Config keys (already in keprix)

| Key | Values | Hermes equivalent |
| --- | --- | --- |
| `display.busy_input_mode` | `interrupt`, `queue`, `steer` | `busyInputMode` in `useConfigSync.ts` |
| `display.details.*` | per-section visibility | `domain/details.ts` |

TUI reads these via `GET /api/config` or a thin `GET /api/tui/config` snapshot.

## Non-goals

- Rebuilding Ink/React in Python
- Changing marketing or web chat UI
- Replacing the web UI approval flow; TUI gets parity overlays only
