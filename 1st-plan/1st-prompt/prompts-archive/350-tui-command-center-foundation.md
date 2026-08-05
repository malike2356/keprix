# Keprix Prompt 350: TUI Command Center Foundation

## Goal

Create the shared foundation for the Keprix TUI Command Center. This is the umbrella architecture that the following prompts will build on. It must not change the Keprix look and feel yet; it creates state models, contracts, test harnesses, and integration slots.

## Required architecture

Create:

```text
src/keprix/tui/command_center/
  __init__.py
  actions.py
  registry.py
  state.py
  layout.py
  telemetry.py
  contracts.py
```

## Required behavior

- Define a typed `CommandCenterAction` model for all TUI actions.
- Create an action registry that can include local commands, sessions, models, skills, plugins, recent files, and runtime actions.
- Create a `CommandCenterState` model that tracks active surface, selected action, focus target, transport mode, current session, queue depth, runtime status, and theme.
- Define layout zones for cockpit, transcript, runtime timeline, sidebar, status bar, overlay, and review mode.
- Add a telemetry model for UI actions without sending data externally.
- Add contracts that future prompts can append to.

## Non-goals

- Do not build the full command palette yet.
- Do not redesign the full TUI yet.
- Do not change runtime behavior.
- Do not copy Hermes styling.

## Tests required

Add:

```text
tests/tui/test_command_center_foundation.py
tests/tui/test_command_center_contracts.py
```

## Acceptance criteria

- Command Center package exists.
- Action registry is pure and tested.
- State model is pure and tested.
- Layout zones are documented in code.
- Existing TUI app can import the foundation without side effects.
- `python -m pytest tests/tui/test_command_center_foundation.py tests/tui/test_command_center_contracts.py -q` passes.
- `python -m pytest tests/tui -q` passes.
- `bash scripts/check-tui-surpass-hermes.sh` passes.
