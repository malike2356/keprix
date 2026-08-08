# Prompt 419 / 03: Hermes-parity curl installer + first run

**Status: COMPLETED 2026-08-07**  
Series: Keprix public GTM + Hermes install parity  
Depends on: 418  
Blocks: 420, 422  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Purpose

Give strangers a Hermes-class primary install:

```bash
curl -fsSL https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh | bash
```

Then a `keprix` command on PATH and a clear first-run setup path.

## Hermes behaviors to match (UX, not code copy)

1. One curl/bash entry (Linux / macOS / WSL2 first; Windows documented separately).
2. Installer clones (or updates) the repo under a stable home:
   - Default: `${KEPRIX_HOME:-$HOME/.keprix}/keprix` (code)
   - Data: `${KEPRIX_HOME:-$HOME/.keprix}` (config, logs, state)
3. Creates an isolated Python env (prefer `uv` if present, else venv/pip).
4. Installs the CLI extra that enables TUI (`[tui]` or equivalent).
5. Puts `keprix` on PATH (`~/.local/bin` symlink or wrapper).
6. Prints next steps: reload shell, `keprix setup` (or equivalent), `keprix tui`.
7. Idempotent: re-run upgrades/updates instead of breaking.

## Tasks

1. Rewrite `scripts/install.sh` so it works when **piped** (do not assume
   `BASH_SOURCE` points at a full checkout). Detect pipe vs checkout mode.
2. Keep `scripts/install-curl.sh` as a thin alias that matches README one-liner.
3. Implement or wire `keprix setup` / existing wizard as the post-install
   interactive step (LLM key, optional channels). Reuse
   `scripts/wizard.py` / installer modules where possible.
4. Support env overrides: `KEPRIX_HOME`, `KEPRIX_REPO_URL`, `KEPRIX_REF`
   (branch/tag), noninteractive `KEPRIX_NONINTERACTIVE=1`.
5. Docker: installer may *offer* Compose full stack, but must not require Docker
   for CLI/TUI-only success (Hermes does not force Docker for chat).
6. Document Windows: WSL2 recommended; native only if already supported and
   tested. No fake claims.
7. Add `tests/installer/` or script smoke that runs installer in a temp HOME
   with a local file:// or mocked clone where feasible. At minimum, dry-run
   mode that validates path layout functions.
8. Until GitHub is public, document that the one-liner fails closed; do not
   pretend raw URLs work.

## Acceptance

- [x] Piped install creates `~/.keprix/keprix` (or `KEPRIX_HOME` layout).
- [x] `keprix --version` works without `source .venv`.
- [x] README one-liner matches the real script URL.
- [x] Re-run is safe (update path).
- [x] Contributor `bash scripts/install.sh` from an existing clone still works.

## What was built

- Rewrote `scripts/install.sh` (pipe vs checkout, `KEPRIX_HOME`/`KEPRIX_REPO_URL`/`KEPRIX_REF`, DRY_RUN, NONINTERACTIVE, optional Docker).
- Thin `scripts/install-curl.sh` with public-repo 404 note.
- `paths.py`: `get_keprix_home()`, install root default `~/.keprix`.
- Smoke test `tests/installer/test_install_sh_hermes_layout.py`.
- README Install (CLI/TUI) + `docs/getting-started/install.md` curl subsection.
- Gap map curl/home rows updated (publicize remains owner-only).

## Verification

```bash
bash -n scripts/install.sh scripts/install-curl.sh
rg -n 'KEPRIX_HOME|piped|curl -fsSL' scripts/install.sh README.md
# After owner publicizes repo, cold install in temp HOME:
# HOME=/tmp/keprix-gtm-test bash scripts/install-curl.sh
```

## Out of scope

- Publishing to PyPI (421).
- Contabo deploy (427).
