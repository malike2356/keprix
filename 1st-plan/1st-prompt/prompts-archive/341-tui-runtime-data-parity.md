# Keprix Prompt 341: TUI Runtime Data Parity

## Goal

Make every Keprix TUI panel and workspace element consume real live runtime data, not only local placeholders or disconnected state models. This closes the biggest remaining Hermes TUI gap while preserving Keprix look and feel.

Hermes feels stronger because its TUI is fed by the running agent: tool calls, subagents, model metadata, session activity, queued work, skills, plugins, and request details are visible while the user works. Keprix must achieve the same behavioral outcome through Keprix-native APIs, typed events, adapters, and registries.

## Scope

Implement real runtime feeds for:

- Details panel
- Tool trace
- Subagent tree
- Message metadata
- API request and response inspector
- Session switcher
- Queued message controls
- Skills hub
- Plugins hub
- Model picker
- Workspace sidebar

## Required behavior

### Details panel

The details panel must show real data for the active turn:

- Current model and provider
- Input tokens, output tokens, total tokens when available
- Cost estimate when available
- Latency per turn
- Temperature and routing metadata when available
- Tool call count
- Subagent count
- Last event time
- Current busy or idle state

It must update while a turn is streaming, not only after completion.

### Tool trace

Tool trace must show:

- Tool name
- Tool call id
- Status: queued, running, done, error, cancelled
- Args summary with secret redaction
- Start time and elapsed time
- Result preview
- Expandable full args and full result in a pager or details pane
- Error type and message for failed tools

Tool updates must come from the live stream when available. If an older backend stream lacks structured tool events, add a typed compatibility adapter that derives best-effort events from existing payloads without breaking old sessions.

### Subagent tree

Subagent tree must show:

- Parent and child relationships
- Subagent name or goal
- Status: queued, running, done, error, cancelled
- Output preview
- Token and cost hints where available
- Start and finish timestamps where available
- Ability to focus a subagent and view its latest events

The tree must update while subagents run.

### Message metadata

Every rendered assistant message must be able to expose:

- Model
- Provider
- Token count
- Latency
- Tool calls made
- Cost estimate when available
- Created timestamp
- Completion status: complete, interrupted, errored

This metadata must be visible in the details panel and available through keyboard selection. Do not clutter the main transcript with excessive metadata by default.

### API inspector

Add a safe API inspector inside the details panel or debug panel:

- Request id
- Provider
- Model
- Timing
- Token usage
- Status
- Sanitized error
- Sanitized request and response preview

Never display secrets, API keys, bearer tokens, cookies, raw credentials, or unredacted tool args.

### Session switcher

The left workspace pane or a dedicated overlay must show:

- Session title
- Preview of latest message
- Last active time
- Busy state if active
- Model if known
- Ability to switch sessions
- Ability to create a new session
- Ability to close or archive a local TUI session entry when supported

Keyboard support is required.

### Queued message controls

Queued message handling must include:

- Queue count in sidebar/status
- Queue list view
- Ability to remove a queued item
- Ability to send next queued item
- Ability to clear queue
- Clear busy-mode explanation: interrupt, queue, steer

### Skills hub

The skills hub must use real skill registry data where available:

- Installed skills
- Enabled or disabled state
- Name
- Description
- Source path or package
- Commands or entry points where available
- Open/read SKILL.md in pager
- Enable/disable or install/uninstall only if supported by existing safe APIs

Do not invent a parallel skill registry.

### Plugins hub

The plugins hub must use real plugin registry data where available:

- Installed plugins
- Enabled or disabled state
- Name
- Description
- Version where available
- Source path or package
- Exposed commands, tools, or providers where available
- Configure, enable, disable only if supported by existing safe APIs

Do not hardcode fake marketplace data.

### Model picker

The model picker must use real model list data:

- Provider
- Model id
- Display name
- Context window where available
- Pricing where available
- Local or remote indicator where available
- Current model marker
- Search/filter
- Select model
- Persist default model only if existing config supports it

## Implementation guidance

Prefer these patterns:

- Add typed TUI event models under `src/keprix/tui/`.
- Add backend adapter methods to `src/keprix/tui/client.py` only where needed.
- Reuse existing APIs before adding routes.
- If a route is needed, add it in the backend with authentication and tests.
- Keep product-specific modules out of `keprix.tui`; expose data through typed APIs or registries.
- Keep UI display Keprix-native.

Likely files:

```text
src/keprix/tui/runtime_events.py
src/keprix/tui/runtime_store.py
src/keprix/tui/details_runtime.py
src/keprix/tui/widgets/details_panel.py
src/keprix/tui/widgets/session_switcher.py
src/keprix/tui/widgets/queued_messages.py
src/keprix/tui/widgets/skills_hub.py
src/keprix/tui/widgets/plugins_hub.py
src/keprix/tui/widgets/model_picker.py
src/keprix/tui/client.py
src/keprix/tui/app.py
tests/tui/test_runtime_data_parity.py
tests/tui/test_details_runtime.py
tests/tui/test_model_picker_runtime.py
tests/tui/test_hubs_runtime.py
```

## Acceptance criteria

- Details panel updates during a live streaming turn.
- Tool trace receives real tool events and shows running, done, and error states.
- Subagent tree receives live subagent spawn and completion events.
- Message metadata is stored and visible through details view.
- API inspector shows sanitized request/response metadata without secrets.
- Session switcher uses real session list data with preview and last active time.
- Queue controls can list, remove, flush, and clear queued messages.
- Skills hub reads real skill data.
- Plugins hub reads real plugin data.
- Model picker reads real model data and can select a model.
- All old TUI tests pass.
- New runtime data parity tests pass.
- No Keprix visual identity regression.

## Verification commands

```bash
python -m pytest tests/tui -q
python -m pytest tests/tui/test_runtime_data_parity.py -q
python -m pytest tests/tui/test_details_runtime.py -q
```

