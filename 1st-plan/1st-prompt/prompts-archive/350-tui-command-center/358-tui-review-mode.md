# Keprix Prompt 358: TUI Review Mode

## Goal

Add a review mode that summarizes what happened in the last turn. This should make Keprix valuable for coding, operations, and security workflows.

## Required review summary

Show:

- User request summary
- Assistant outcome summary
- Files changed
- Tools used
- Subagents used
- Commands executed
- Risks or warnings
- Tests run
- Pending next actions
- Token usage, latency, and cost

## Required UX

- Open with `Ctrl+R` and command palette action.
- It must be readable as a compact report.
- It must support copy summary.
- It must work even when only partial runtime data exists.
- It must not invent facts that are not in runtime data.

## Required files

Create or update:

```text
src/keprix/tui/command_center/review.py
src/keprix/tui/widgets/review_mode.py
src/keprix/tui/runtime_store.py
src/keprix/tui/app.py
```

## Tests required

Add:

```text
tests/tui/test_review_mode_model.py
tests/tui/test_review_mode_partial_data.py
tests/tui/test_review_mode_copy.py
```

## Acceptance criteria

- Review mode opens with keybinding and action.
- Review summary uses runtime data only.
- Partial data produces a useful summary without false claims.
- Copy action returns the rendered review text.
- `python -m pytest tests/tui/test_review_mode_model.py tests/tui/test_review_mode_partial_data.py tests/tui/test_review_mode_copy.py -q` passes.
- `python -m pytest tests/tui -q` passes.
- `bash scripts/check-tui-surpass-hermes.sh` passes.
