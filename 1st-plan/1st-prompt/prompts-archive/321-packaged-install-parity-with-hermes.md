# Keprix Prompt 321: Packaged Install Parity With Hermes

## Purpose

Make Keprix feel like Hermes for users: install once, run `keprix`, no manual venv, no `PYTHONPATH`.

## Tasks

1. Verify `pyproject.toml` exposes the `keprix` console script.
2. Verify `keprix[tui]` installs Textual and all TUI runtime dependencies.
3. Add a smoke script:
   - `scripts/smoke-pipx-install.sh`
4. The script must test:
   - `pipx install '.[tui]'`
   - `keprix --help`
   - `keprix tui --help`
   - `keprix --version` or equivalent
   - import of `keprix.tui.app`
5. Add docs:
   - `docs/getting-started/install.md`
   - update TUI docs to remove development-only commands from the primary path.

## User-facing target

```bash
pipx install 'keprix[tui]'
keprix start
keprix tui
```

For local checkout:

```bash
pipx install '.[tui]'
keprix tui
```

## Acceptance criteria

- The primary docs do not require `.venv/bin/activate`.
- Development docs may mention `.venv`, but only for contributors.
- The TUI command works from outside the repo after pipx install.

## Verification

```bash
bash scripts/smoke-pipx-install.sh
python -m pytest tests/tui -q
```
