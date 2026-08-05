# TUI freeze and Hermes parity

Keprix TUI is core runtime. It is not a product surface for feature-specific imports, and it is not a place to copy Hermes visual identity. Hermes is a reference for runtime quality, interaction reliability, keyboard ergonomics, and gateway behavior only.

Keprix keeps its own UI/UX, brand expression, visual system, navigation, colors, typography, and product feel.

## Freeze rule

`src/keprix/tui/` is frozen for generic TUI improvements and bug fixes only.

Allowed changes:

- Fix TUI bugs.
- Improve keyboard behavior.
- Improve streaming, queue, steer, approval, clarify, setup, slash, and transcript behavior.
- Improve performance or resilience.
- Add generic display support for data returned by an API.

Not allowed:

- Import product modules into `keprix.tui`.
- Hardcode Agent OS, Channel Shield, billing, Scout, or app-specific behavior into TUI runtime.
- Copy Hermes visual identity, branding, colors, spacing, typography, or layout.
- Add product-specific panels directly into core TUI.

Product features may expose TUI data through backend APIs, slash commands, and generic registries.

## References

Hermes reference files:

- `1st-plan/competitor-research/00-agents-to-adopt/hermes-agent/ui-tui/src/app.tsx`
- `1st-plan/competitor-research/00-agents-to-adopt/hermes-agent/ui-tui/src/app/useSubmission.ts`
- `1st-plan/competitor-research/00-agents-to-adopt/hermes-agent/ui-tui/src/app/useConfigSync.ts`
- `1st-plan/competitor-research/00-agents-to-adopt/hermes-agent/ui-tui/src/app/createGatewayEventHandler.ts`
- `1st-plan/competitor-research/00-agents-to-adopt/hermes-agent/ui-tui/src/app/gatewayRecovery.ts`
- `1st-plan/competitor-research/00-agents-to-adopt/hermes-agent/ui-tui/src/app/spawnHistoryStore.ts`
- `1st-plan/competitor-research/00-agents-to-adopt/hermes-agent/ui-tui/src/components/activeSessionSwitcher.tsx`
- `1st-plan/competitor-research/00-agents-to-adopt/hermes-agent/ui-tui/src/components/streamingMarkdown.tsx`
- `1st-plan/competitor-research/00-agents-to-adopt/hermes-agent/ui-tui/src/components/textInput.tsx`
- `1st-plan/competitor-research/00-agents-to-adopt/hermes-agent/tui_gateway/server.py`
- `1st-plan/competitor-research/00-agents-to-adopt/hermes-agent/tui_gateway/ws.py`
- `1st-plan/competitor-research/00-agents-to-adopt/hermes-agent/tui_gateway/slash_worker.py`

Keprix files:

- `src/keprix/tui/app.py`
- `src/keprix/tui/client.py`
- `src/keprix/tui/slash_handler.py`
- `src/keprix/tui/slash_commands.py`
- `src/keprix/tui/slash_registry.py`
- `src/keprix/tui/composer.py`
- `src/keprix/tui/transcript_store.py`
- `src/keprix/tui/widgets/virtual_transcript.py`
- `src/keprix/tui/widgets/approval_overlay.py`
- `src/keprix/tui/widgets/clarify_overlay.py`
- `src/keprix/tui/widgets/setup_required.py`
- `src/keprix/tui/streaming_markdown.py`
- `src/keprix/tui/external_editor.py`
- `src/keprix/tui/voice.py`
- `tests/tui/`
- `tests/architecture/test_core_product_boundaries.py`

## Parity matrix

| Area | Hermes reference | Keprix reference | Status | Action |
| --- | --- | --- | --- | --- |
| Session list and resume | `activeSessionSwitcher.tsx`, `useSessionLifecycle.ts` | `app.py`, `client.py`, `tests/tui/test_client_sessions.py` | same | Keep Keprix Textual UI; preserve behavior. |
| Streaming chat | `streamingAssistant.tsx`, `streamingMarkdown.tsx`, `gatewayClient.ts` | `app.py`, `client.py`, `streaming_markdown.py`, `tests/tui/test_streaming.py` | same | Keep tests around chunk handling and markdown stability. |
| Busy input: interrupt, queue, steer | `useSubmission.ts`, `useConfigSync.ts`, `uiStore.ts` | `app.py`, `client.py`, `slash_commands.py`, `tests/tui/test_busy_input.py` | same | Keep behavior. Do not change visual surface. |
| Slash local commands | `createSlashHandler.ts`, `domain/slash.ts` | `slash_handler.py`, `slash_commands.py`, `slash_registry.py`, `tests/tui/test_slash_registry.py` | same | Keep backend fallthrough and local completion. |
| Slash backend fallthrough | `tui_gateway/slash_worker.py`, `gatewayClient.ts` | `slash_handler.py`, `client.py`, `tests/tui/test_slash_fallthrough.py` | same | Keep command dispatch behind API, not product imports. |
| Clarify overlay | `overlayStore.ts`, `components/appOverlays.tsx` | `widgets/clarify_overlay.py`, `tests/tui/test_clarify_overlay.py` | same | Keep generic overlay. |
| Approval overlay | `approvalAction.test.ts`, `components/appOverlays.tsx` | `widgets/approval_overlay.py`, `tests/tui/test_approval_overlay.py` | same | Keep generic approval behavior. |
| Virtual scrollback | `hooks/useVirtualHistory.ts`, `virtualHistory*.test.ts` | `widgets/virtual_transcript.py`, `transcript_store.py`, `tests/tui/test_virtual_transcript.py` | same | Keep transcript virtualization tests. |
| Selection and clipboard | `clipboard.test.ts`, `osc52.test.ts` | `clipboard.py`, `selection.py`, `tests/tui/test_clipboard_osc52.py`, `tests/tui/test_selection.py` | same | Preserve OSC52 and local clipboard fallback. |
| External editor compose | `lib/editor.ts`, `lib/editor.test.ts` | `external_editor.py`, `tests/tui/test_external_editor.py` | same | Keep `$EDITOR` handoff generic. |
| Voice push-to-talk | not primary in listed Hermes files | `voice.py`, `tests/tui/test_voice.py` | Keprix better | Preserve as Keprix extension. |
| Setup overlay and handoff | `setupHandoff.ts`, `content/setup.ts` | `widgets/setup_required.py`, `setup_handoff.py`, `tests/tui/test_setup_handoff.py` | same | Keep one-screen unblock plus full setup handoff. |
| Gateway recovery | `gatewayRecovery.ts`, `createGatewayEventHandler.ts`, `gatewayRecovery.test.ts` | `client.py`, `app.py` | Hermes better | Add a future generic recovery prompt. |
| Active session switcher ergonomics | `activeSessionSwitcher.tsx`, `activeSessionSwitcher.test.ts` | `app.py`, `tests/tui/test_client_sessions.py` | Hermes better | Add a future prompt for faster keyboard session switching. |
| Spawn history and replay archive | `spawnHistoryStore.ts`, `spawnHistoryStore.test.ts` | no direct equivalent | Hermes better | Add future prompt if agent spawn replay remains a product goal. |
| Skin and theme sync | `theme.test.ts`, `components/themed.tsx` | `styles/theme.tcss`, no gateway theme sync | Hermes better | Add future prompt for Keprix-branded theme sync only. |
| Terminal platform edge tests | `terminalParity.test.ts`, `termux.test.ts`, `terminalSetup.test.ts` | `terminal_modes.py`, `tests/tui/test_client.py` | Hermes better | Add future prompt for platform matrix coverage. |
| Visual identity | Hermes components and branding | Keprix Textual theme and product UI | different by design | Do not copy Hermes visual identity. |

## High-value follow-up prompts

These are behavior prompts only. They must keep Keprix UI/UX and branding.

### TUI gateway recovery parity

Implement Hermes-grade gateway recovery behavior in Keprix TUI:

- reconnect notices
- recoverable event handling
- clear stale stream state
- preserve composer text during reconnect
- tests for disconnect during stream and reconnect after idle

References:

- `ui-tui/src/app/gatewayRecovery.ts`
- `ui-tui/src/app/createGatewayEventHandler.ts`
- `ui-tui/src/__tests__/gatewayRecovery.test.ts`
- `src/keprix/tui/client.py`
- `src/keprix/tui/app.py`

### TUI session switching ergonomics

Improve Keprix session switching behavior without copying Hermes layout:

- faster keyboard switcher
- fuzzy session matching
- recent session priority
- no product-specific imports

References:

- `ui-tui/src/components/activeSessionSwitcher.tsx`
- `ui-tui/src/__tests__/activeSessionSwitcher.test.ts`
- `src/keprix/tui/app.py`
- `tests/tui/test_client_sessions.py`

### TUI platform parity coverage

Add Keprix tests for terminal platform behavior:

- truecolor handling
- Termux behavior
- mouse mode toggles
- narrow terminal layout
- paste bursts

References:

- `ui-tui/src/__tests__/terminalParity.test.ts`
- `ui-tui/src/__tests__/terminalSetup.test.ts`
- `ui-tui/src/__tests__/termux.test.ts`
- `src/keprix/tui/terminal_modes.py`
- `tests/tui/`

### Keprix-branded theme sync

Add generic theme sync while preserving Keprix design:

- backend theme config
- TUI theme refresh
- no Hermes colors or branding
- tests for loading and fallback

References:

- `ui-tui/src/components/themed.tsx`
- `ui-tui/src/__tests__/theme.test.ts`
- `src/keprix/tui/styles/theme.tcss`

## Current gate

The architecture boundary test enforces that TUI does not import product modules:

```bash
python -m pytest tests/architecture/test_core_product_boundaries.py -q
```

The current TUI regression suite is:

```bash
python -m pytest tests/tui -q
```
