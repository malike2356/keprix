# Keprix Prompt 360: TUI Keyboard Polish and Final Proof

## Goal

Finish the Keprix TUI Command Center series with a consistent keyboard model, final proof harness updates, and a concise comparison report.

## Required keymap

Implement:

- `Ctrl+P`: command palette
- `Ctrl+Space`: command palette
- `Ctrl+L`: transcript search
- `Ctrl+S`: sessions or session map
- `Ctrl+M`: model picker
- `Ctrl+R`: review mode
- `Ctrl+K`: send or flush queue, preserving existing behavior
- `Esc`: close overlays
- `?`: help overlay

## Required behavior

- Keybindings must be discoverable in help.
- Escape must close every new overlay and restore focus.
- Existing bindings must not regress.
- Command palette actions must mirror keybindings.
- Help must remain reachable offline.

## Proof harness updates

Update:

```text
src/keprix/tui/surpass_contract.py
docs/architecture/tui-surpass-hermes-contract.md
scripts/check-tui-surpass-hermes.sh
```

Add a new Command Center proof group covering:

- Command palette
- Cockpit first screen
- Runtime timeline
- Tool cards
- Session map
- Themes
- Status bar
- Review mode
- Empty/loading/error states
- Keyboard model

## Tests required

Add:

```text
tests/tui/test_keyboard_model.py
tests/tui/test_command_center_final_contract.py
tests/tui/test_command_center_surpass_proof.py
```

## Acceptance criteria

- All keybindings work or are represented by tested action dispatch.
- Final proof harness passes.
- Command Center proof group is documented.
- Pending prompt README is updated with evidence.
- All prompts 350-360 are archived after completion.
- `python -m pytest tests/tui/test_keyboard_model.py tests/tui/test_command_center_final_contract.py tests/tui/test_command_center_surpass_proof.py -q` passes.
- `python -m pytest tests/tui -q` passes.
- `bash scripts/check-tui-surpass-hermes.sh` passes.
