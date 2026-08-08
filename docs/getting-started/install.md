# Install Keprix

## Curl installer (CLI / TUI)

Primary install path for Linux, macOS, and WSL2:

```bash
curl -fsSL https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh | bash
```

The installer clones or updates code under `${KEPRIX_HOME:-$HOME/.keprix}/keprix`, creates an isolated Python env (prefers `uv` when available), installs the `[tui]` extra, and puts `keprix` on PATH via `~/.local/bin`.

The repository and raw installer are publicly readable. The curl command follows
the development channel. Stable distribution uses `scripts/install-release.sh`
with an exact version, manifest checksum, and signature verification.

**Windows:** use WSL2 and run the installer inside Linux. Native Windows is not claimed.

Env overrides: `KEPRIX_HOME`, `KEPRIX_REPO_URL`, `KEPRIX_REF`, `KEPRIX_NONINTERACTIVE=1`, `KEPRIX_DRY_RUN=1`, optional `KEPRIX_INSTALL_DOCKER=1` (Compose is never required for CLI success).

Next steps after install: `hash -r`, `keprix --version`, `keprix setup`, `keprix tui`.

---

## Requirements (pipx paths)

For workstation installs with `pipx` (GitHub or local checkout), you need:

- Python 3.11 or 3.12
- pipx
- At least one LLM provider key for agent replies

Install pipx if needed:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

Restart your shell after `ensurepath` if `pipx` is not immediately available.

## Install with pipx from GitHub

Alternative to the curl installer when you want pipx to manage an isolated env from the public repo:

```bash
pipx install 'keprix[tui] @ git+https://github.com/malike2356/keprix.git'
keprix --version
keprix start --host 127.0.0.1 --port 3333
```

In another terminal:

```bash
keprix tui
```

Use `keprix tui --help` for terminal UI flags such as session resume, model override, API URL, bearer token, and mouse capture.

**Public repo required:** anonymous `git+https://github.com/malike2356/keprix.git` fails until the repository is public. See [public GitHub checklist](../operations/public-github-checklist.md).

**PyPI note:** the package name `keprix` is **not published on PyPI** yet (404 as of 2026-08-07). Bare PyPI installs of the `keprix[tui]` extra (no `@ git+...` URL) are **not** supported and will 404 until an owner publish. When publish is approved, follow [PyPI publish checklist](../operations/pypi-publish-checklist.md).

## Install from a local checkout

From the repository root:

```bash
pipx install '.[tui]' --force
keprix --version
keprix tui --help
```

Use this when testing a local build or when the public git URL is not yet reachable.

## Voice extras

The terminal UI can use push-to-talk voice capture with the voice extra.

From GitHub (same public-repo caveat as above):

```bash
pipx install 'keprix[tui-voice] @ git+https://github.com/malike2356/keprix.git'
```

From a checkout:

```bash
pipx install '.[tui-voice]' --force
```

Bare PyPI installs of the `keprix[tui-voice]` extra (no git URL) are not supported until publish.

## Contributor install (secondary)

Use a repository virtual environment only when changing Keprix itself:

```bash
bash scripts/install.sh
source .venv/bin/activate
```

Normal users should not need `PYTHONPATH`, an activated development venv, or manual module entry points to run `keprix tui`. For bare-metal Postgres/Redis/Node, see [Manual install (for developers)](manual-install.md).

## Next

- [First run](first-run.md)
- [Quickstart](quickstart.md) (Docker Compose full stack)

## Uninstall / reset

**CLI home:** remove `${KEPRIX_HOME:-$HOME/.keprix}`. This deletes local install code, config, and any keys stored under that tree. Confirm before deleting.

Optional: remove the `keprix` symlink if you no longer want the command:

```bash
rm -f ~/.local/bin/keprix
```

**Docker:** stop the stack from a checkout that has `docker/docker-compose.yml`:

```bash
docker compose -f docker/docker-compose.yml down
```

Add `-v` only if you accept deleting Compose volumes (database and other persisted data):

```bash
docker compose -f docker/docker-compose.yml down -v
```
