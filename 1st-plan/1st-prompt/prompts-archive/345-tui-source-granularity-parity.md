# Keprix Prompt 345: TUI Source Granularity Parity

## Goal

Refactor Keprix TUI into a Hermes-level granular architecture without copying Hermes file names blindly and without changing Keprix look and feel. The goal is finer ownership, better tests, easier fault isolation, better renderer evolution, and lower risk for future TUI work.

Hermes has many more TUI source files because it separates renderer primitives, input handling, command handling, overlays, panels, terminal features, and state into small modules. Keprix currently has fewer files and some modules carry too many responsibilities. This prompt splits Keprix TUI into a disciplined, granular architecture with tests per contract.

## Non-goals

- Do not chase a numeric file count as a vanity metric.
- Do not copy Hermes visual identity.
- Do not duplicate logic already cleanly abstracted.
- Do not move product-specific code into TUI core.
- Do not break imports for existing CLI entry points.

## Target architecture

Create explicit subpackages under `src/keprix/tui/`:

```text
src/keprix/tui/
  commands/
  composer/
  contracts/
  gateway/
  layout/
  overlays/
  panels/
  renderer/
  runtime/
  search/
  sessions/
  terminal/
  widgets/
```

Use compatibility exports where needed so existing imports continue to work during the transition.

## Required module splits

### Commands

Move slash-related behavior into `tui/commands/`:

```text
commands/schema.py
commands/registry.py
commands/completion.py
commands/preview.py
commands/args.py
commands/dispatch.py
commands/history.py
commands/fuzzy.py
```

Contracts:

- All commands have schema metadata.
- Completion is independent from rendering.
- Preview is independent from dispatch.
- Dispatch has local/backend/skill/plugin paths.
- Old imports from `slash_registry.py`, `slash_commands.py`, `slash_handler.py`, and `slash_arg_parser.py` remain as compatibility wrappers.

### Composer

Move input and queue behavior into `tui/composer/`:

```text
composer/history.py
composer/queue.py
composer/paste.py
composer/metrics.py
composer/external_editor.py
composer/voice.py
composer/busy_modes.py
```

Contracts:

- 10K input history remains.
- Queue, steer, interrupt modes remain tested.
- Paste collapse remains tested.
- External editor remains tested.
- Voice compose remains tested.

### Renderer

Move rendering primitives into `tui/renderer/`:

```text
renderer/cells.py
renderer/measure.py
renderer/diff.py
renderer/markdown.py
renderer/code_blocks.py
renderer/messages.py
renderer/selection.py
renderer/viewport.py
renderer/theme.py
renderer/snapshots.py
```

Contracts:

- Text measurement handles Unicode width.
- Diff model can compare frames.
- Markdown renderer remains streaming-safe.
- Message renderer remains Keprix-themed.
- Selection and viewport tests remain green.

### Runtime

Move runtime state into `tui/runtime/`:

```text
runtime/events.py
runtime/store.py
runtime/adapters.py
runtime/details.py
runtime/tools.py
runtime/subagents.py
runtime/messages.py
runtime/api_inspector.py
```

Contracts:

- Existing `runtime_events.py`, `runtime_store.py`, `details_runtime.py` become compatibility wrappers.
- Runtime data parity tests still pass.

### Panels and overlays

Move panel logic out of generic widgets where appropriate:

```text
panels/details.py
panels/sessions.py
panels/queue.py
panels/skills.py
panels/plugins.py
panels/model_picker.py
panels/debug.py
panels/help.py
overlays/approval.py
overlays/clarify.py
overlays/setup.py
overlays/pager.py
```

Contracts:

- All existing overlay tests pass.
- Existing widget imports remain compatible.
- Panels have pure state models plus Textual surfaces.

### Terminal

Move terminal behavior into `tui/terminal/`:

```text
terminal/capabilities.py
terminal/startup.py
terminal/modes.py
terminal/raw.py
terminal/title.py
terminal/notifications.py
terminal/clipboard.py
terminal/platform.py
terminal/resize.py
terminal/links.py
```

Contracts:

- Existing terminal tests pass.
- Compatibility wrappers remain.
- Termux/basic terminal degradation remains tested.

## Tests required

Add:

```text
tests/tui/test_granularity_contract.py
tests/tui/test_import_compatibility.py
tests/tui/test_renderer_contracts.py
tests/tui/test_command_contracts.py
tests/tui/test_runtime_contracts.py
```

The granularity contract must verify:

- Required subpackages exist.
- Compatibility wrappers import successfully.
- No circular imports in core TUI packages.
- TUI core does not import product modules directly.
- Each new subpackage has tests.

## Acceptance criteria

- TUI is split into granular subpackages with compatibility wrappers.
- No user-facing behavior regresses.
- `python -m pytest tests/tui -q` passes.
- `bash scripts/check-tui-parity.sh` passes.
- New granularity contract passes.
- Source count increases for real architectural reasons, not empty files.
- Keprix look and feel unchanged.

## Verification commands

```bash
python -m pytest tests/tui -q
python -m pytest tests/tui/test_granularity_contract.py -q
bash scripts/check-tui-parity.sh
```

