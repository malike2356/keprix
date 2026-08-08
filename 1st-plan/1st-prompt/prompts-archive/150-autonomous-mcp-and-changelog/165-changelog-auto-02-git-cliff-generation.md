# Keprix Prompt 165: Changelog automation 02 - git-cliff generation

## Purpose

Add [git-cliff](https://git-cliff.org/) so unreleased changelog entries can be **generated
from git history** in Keep a Changelog format compatible with `parseChangelog()`.

Depends on Prompt **164** (conventional commits enforced).

Read reference **163** and `docs/operations/changelog-automation.md`.

**Writer policy:** git-cliff is **preview + CI drift check only**. release-please (Prompt 166)
owns merged version sections. Do not auto-commit changelog on every push to main.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## What to build

### 1. Install git-cliff in CI

Pin version in workflow (example `v2.7.0`). Options:

- `cargo install git-cliff` in workflow (slow), or
- Download release binary from GitHub releases, or
- `npm install -g git-cliff` if npm package maintained.

Prefer official binary install in `.github/workflows/changelog-generate.yml` and
`scripts/changelog-preview.sh`.

### 2. `cliff.toml` at repo root

Configure Keep a Changelog output. Minimum requirements:

```toml
[changelog]
header = "# Changelog\n\nAll notable changes to this project are documented in this file.\n\nThe format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),\nand this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n"
body = """
{% if version %}\
    {% if version == \"Unreleased\" %}\
        ## [Unreleased]\n\
    {% else %}\
        ## [{{ version | trim_start_matches(pat=\"v\") }}] - {{ timestamp | date(format=\"%Y-%m-%d\") }}\n\
    {% endif %}\
{% else %}\
    ## [Unreleased]\n\
{% endif %}\
{% for group, commits in commits | group_by(attribute=\"group\") %}
    ### {{ group | upper_first }}
    {% for commit in commits %}
        - {% if commit.scope %}**{{ commit.scope }}:** {% endif %}{{ commit.message | upper_first }}\
    {% endfor %}
{% endfor %}\n
"""
trim = true

[git]
conventional_commits = true
filter_unconventional = true
split_commits = false
commit_parsers = [
  { message = "^feat", group = "Added" },
  { message = "^fix", group = "Fixed" },
  { message = "^perf", group = "Changed" },
  { message = "^refactor", group = "Changed" },
  { message = "^docs", skip = true },
  { message = "^style", skip = true },
  { message = "^test", skip = true },
  { message = "^chore", skip = true },
  { message = "^ci", skip = true },
  { message = "^build", skip = true },
]

[bump]
features_always_bump_minor = true
breaking_always_bump_major = true
```

Tune `commit_parsers` until sample output parses correctly.

**Validate** against `frontend/src/lib/changelog.ts` regexes:

- `## [Unreleased]`
- `## [0.1.0] - 2026-07-05`
- `### Added` / `### Fixed` / etc.
- `- item` bullets

### 3. `scripts/changelog-preview.sh`

```bash
#!/usr/bin/env bash
# Print unreleased changelog section to stdout (does not write files).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
git-cliff --unreleased --config cliff.toml
```

Add `scripts/changelog-generate-full.sh` (optional) to render entire file to stdout for
maintainer diff review.

### 4. Extend `scripts/check-changelog-sync.sh`

After docs sync check, add **optional drift warning** (non-blocking in Prompt 165, blocking
after Prompt 166):

```bash
if command -v git-cliff >/dev/null 2>&1; then
  PREVIEW="$(git-cliff --unreleased --config cliff.toml 2>/dev/null || true)"
  if [[ -n "$PREVIEW" ]]; then
    echo "git-cliff unreleased preview available (run scripts/changelog-preview.sh)"
  fi
fi
```

### 5. CI workflow `.github/workflows/changelog-generate.yml`

```yaml
name: Changelog preview

on:
  pull_request:
    paths:
      - "**/*"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  preview:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Install git-cliff
        run: |
          curl -fsSL "https://github.com/orhun/git-cliff/releases/download/v2.7.0/git-cliff-2.7.0-x86_64-unknown-linux-gnu.tar.gz" | tar xz
          sudo mv git-cliff-2.7.0/git-cliff /usr/local/bin/
      - name: Unreleased preview
        run: bash scripts/changelog-preview.sh | tee changelog-preview.md
      - name: Upload preview artifact
        uses: actions/upload-artifact@v4
        with:
          name: changelog-unreleased-preview
          path: changelog-preview.md
```

On PRs, post preview as comment (optional stretch; use `actions/github-script` if time permits).

### 6. Parser tests

`tests/frontend/test_changelog_parser.py`:

```python
from pathlib import Path
import subprocess

from keprix...  # use frontend parser via node OR duplicate parse logic in Python test

# Better: test Python port of parseChangelog or invoke ts via subprocess.
# Minimal: read cliff sample fixture and assert parseChangelog from a small JS test file.
```

Pragmatic approach: add `frontend/src/lib/changelog.test.ts` (Vitest) or Python test that
duplicates regex parsing from `changelog.ts` against fixtures in
`tests/fixtures/changelog-samples/*.md`.

Fixtures:

- `unreleased-only.md`
- `released-and-unreleased.md`
- `git-cliff-sample-output.md` (captured from `changelog-preview.sh`)

### 7. Docs

Update `docs/operations/changelog-automation.md`:

- Document `bash scripts/changelog-preview.sh`.
- Document `cliff.toml` customization.
- Note git-cliff does not write `CHANGELOG.md` until Prompt 166.

## Acceptance criteria

- [ ] `cliff.toml` produces Keep a Changelog markdown parseable by marketing page.
- [ ] `scripts/changelog-preview.sh` prints unreleased section from git history.
- [ ] CI uploads unreleased preview artifact on PRs.
- [ ] Parser tests cover git-cliff sample output.
- [ ] `docs` and `cliff.toml` skip `docs`/`chore`/`ci` commits by default.
- [ ] No automatic commits to `CHANGELOG.md` on main (release-please owns that in Prompt 166).

## Verification

```bash
# After several conventional commits on a branch:
bash scripts/changelog-preview.sh
python3 scripts/generate_doc_pages.py --docs-dir docs --only changelog
cd frontend && pnpm dev   # /changelog still renders
```

Compare preview output categories with manual `CHANGELOG.md` Unreleased section.
