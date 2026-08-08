# PyPI publish checklist (owner only)

**Audience:** Owner only. Agents prepare honesty docs and metadata; they must
**not** upload to PyPI unless the owner explicitly asks in-session.

**Related:** [install.md](../getting-started/install.md),
[public GitHub checklist](public-github-checklist.md).

Never paste secret tokens, API keys, or Twine passwords into this document.

## Before publish

1. Confirm package name `keprix` is still available on PyPI and is the intended
   name (`https://pypi.org/pypi/keprix/json`; expect 404 until first upload).
2. Confirm version in `pyproject.toml` `[project].version` matches the release
   you intend to ship.
3. Confirm `LICENSE` is MIT and `README.md` is present (already wired via
   `readme` / `license-files` in `pyproject.toml`).
4. Confirm package data does not include secrets: no `.env`, no credentials,
   no `.access/` material. Setuptools package-data today is limited to
   `keprix.upgrade` and `keprix.upstream` YAML/templates only.
5. Confirm public GitHub (or the release tag source) matches what strangers
   will install after docs switch to bare pipx.

## Build (local)

```bash
cd /path/to/keprix
python3 -m pip install --user build twine
python3 -m build
# Inspect dist/ for unexpected files before upload
```

## Upload (only when owner asks)

- Prefer trusted publishing (OIDC) from CI when configured, or Twine to PyPI
  with owner credentials held outside the repo.
- Do not commit tokens. Do not paste tokens into docs, chat, or CI logs.
- Example shape only (owner fills secrets out of band):

```bash
python3 -m twine upload dist/*
```

## After successful publish

1. Set docs to allow bare `pipx install 'keprix[tui]'` (and voice extra) as a
   supported path alongside curl and git URL.
2. Set env/marker `KEPRIX_PYPI_PUBLISHED=1` for
   `scripts/check-pypi-docs-honesty.sh` (and later public GTM gate 426) so the
   honesty check no longer fails on bare PyPI prescriptions.
3. Re-verify: `pip index versions keprix` (or equivalent) shows the released
   version; smoke `pipx install 'keprix[tui]'` on a clean machine.

## Honesty until then

Until publish succeeds, primary install remains curl /
`bash scripts/install.sh`, and pipx must use a **git** URL or local checkout.
See install docs for the exact commands.
