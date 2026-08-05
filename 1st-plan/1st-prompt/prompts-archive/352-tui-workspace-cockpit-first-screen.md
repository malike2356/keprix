# Keprix Prompt 352: TUI Workspace Cockpit First Screen

## Goal

Replace the empty-start feeling with a useful Keprix workspace cockpit when the TUI launches or no transcript is active.

## Required cockpit content

Show compact operational sections:

- Active session
- Selected model
- Runtime transport mode
- Backend health
- Recent sessions
- Queue state
- Available skills
- Available plugins
- Quick actions
- Setup or provider warning when needed

## Required UX

- No marketing copy.
- No large hero treatment.
- Dense but readable terminal layout.
- Strong contrast in all supported themes.
- Works offline.
- Updates when sessions, models, skills, plugins, or runtime status refresh.
- Keyboard focus can move from cockpit actions into chat or command palette.

## Required files

Create or update:

```text
src/keprix/tui/command_center/cockpit.py
src/keprix/tui/widgets/workspace_cockpit.py
src/keprix/tui/app.py
```

## Tests required

Add:

```text
tests/tui/test_workspace_cockpit.py
tests/tui/test_workspace_cockpit_offline.py
```

## Acceptance criteria

- Fresh launch has a useful first screen.
- Empty transcript state uses cockpit instead of blank space.
- All cockpit actions are represented as `CommandCenterAction`.
- Offline mode still renders without traceback.
- `python -m pytest tests/tui/test_workspace_cockpit.py tests/tui/test_workspace_cockpit_offline.py -q` passes.
- `python -m pytest tests/tui -q` passes.
- `bash scripts/check-tui-surpass-hermes.sh` passes.
