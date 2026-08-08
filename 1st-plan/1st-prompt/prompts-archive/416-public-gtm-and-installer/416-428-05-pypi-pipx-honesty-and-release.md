# Prompt 421 / 05: PyPI / pipx honesty and release package path

**Status: COMPLETED 2026-08-07**  

Series: Keprix public GTM + Hermes install parity  
Depends on: 418  
Blocks: 422, 426  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Purpose

Stop documenting install paths that 404. Either publish `keprix` to PyPI or
make docs/installer tell the truth: install from GitHub checkout / curl clone.

## Facts

- `https://pypi.org/pypi/keprix/json` returned 404 as of 2026-08-07.
- `docs/getting-started/install.md` tells users `pipx install 'keprix[tui]'`.

## Tasks

1. Choose and document one public policy in `docs/getting-started/install.md`:
   - **Preferred GTM:** curl installer clones GitHub and installs editable/path
     package into user env (419). pipx from **git URL** is an allowed alternative:
     `pipx install 'keprix[tui] @ git+https://github.com/malike2356/keprix.git'`
     (verify exact pipx/pep508 syntax that works).
   - **Optional later:** PyPI publish checklist for owner (twine, trusted
     publishing, package name availability). Do **not** upload in this prompt
     unless owner explicitly asks in-session.
2. Remove or gate any claim that `pipx install 'keprix[tui]'` works from PyPI
   until upload succeeds.
3. Add `docs/operations/pypi-publish-checklist.md` for the day owner publishes
   (version from `pyproject.toml`, LICENSE, README, no secrets in package data).
4. Ensure `pyproject.toml` package metadata is complete for an eventual upload
   (name, version, description, urls, optional `[tui]` extra).
5. Add a CI or gate check that fails if docs still prescribe bare PyPI install
   while a marker file or env says `KEPRIX_PYPI_PUBLISHED!=1` (implement simply
   in 426 if easier).

## Acceptance

- [x] install.md has zero false PyPI claims.
- [x] At least one working non-PyPI install path is documented end-to-end.
- [x] PyPI checklist exists for owner-operated publish.
- [x] No credential files included in package data.

## Verification

```bash
rg -n "pipx install 'keprix" docs/getting-started/install.md README.md || true
rg -n 'pypi.org|PyPI' docs/getting-started/install.md docs/operations/pypi-publish-checklist.md
python - <<'PY'
import tomllib
from pathlib import Path
data = tomllib.loads(Path('pyproject.toml').read_text())
assert data['project']['name'] == 'keprix'
assert 'version' in data['project'] or 'version' in data.get('project', {})
print('ok', data['project'].get('version') or data.get('tool', {}))
PY
```

## What was built

- Honest install policy in `docs/getting-started/install.md` (curl primary; pipx from git URL; checkout; no bare PyPI).
- `docs/features/tui.md` voice/optional deps use git URL or checkout only.
- `docs/operations/pypi-publish-checklist.md` for owner-operated publish (no upload in this prompt).
- `pyproject.toml` keywords, classifiers, `[project.urls]`; package-data unchanged (no `.env`).
- `scripts/check-pypi-docs-honesty.sh` gated by `KEPRIX_PYPI_PUBLISHED`.
- Gap map + series README marked 421 DONE; publish remains owner later.
