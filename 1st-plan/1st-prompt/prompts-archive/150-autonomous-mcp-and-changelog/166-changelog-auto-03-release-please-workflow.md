# Keprix Prompt 166: Changelog automation 03 - release-please workflow

## Purpose

Automate **version bumps**, `CHANGELOG.md` finalization, **git tags**, and **GitHub
Releases** using [release-please](https://github.com/googleapis/release-please).

Depends on Prompts **164** (conventional commits) and **165** (git-cliff preview for PR review).

Read reference **163** and `docs/operations/changelog-automation.md`.

After this prompt, maintainers **merge a release-please PR** instead of hand-moving
Unreleased to a version heading and manually tagging.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## What to build

### 1. release-please config

**`release-please-config.json`:**

```json
{
  "packages": {
    ".": {
      "release-type": "python",
      "package-name": "keprix",
      "changelog-path": "CHANGELOG.md",
      "bump-minor-pre-major": true,
      "bump-patch-for-minor-pre-major": true,
      "include-component-in-tag": false,
      "changelog-sections": [
        { "type": "feat", "section": "Added" },
        { "type": "fix", "section": "Fixed" },
        { "type": "perf", "section": "Changed" },
        { "type": "refactor", "section": "Changed" },
        { "type": "revert", "section": "Changed" }
      ]
    }
  },
  "pull-request-title-pattern": "chore${scope}: release${component} ${version}",
  "changelog-type": "default"
}
```

**`.release-please-manifest.json`:**

```json
{
  ".": "0.1.0"
}
```

Sync manifest version with latest released entry in `CHANGELOG.md` at implementation time.

If frontend needs separate versioning later, add `frontend` package entry; v1 stays
single root package only.

### 2. GitHub workflow `.github/workflows/release-please.yml`

```yaml
name: Release Please

on:
  push:
    branches: [main]

permissions:
  contents: write
  pull-requests: write

jobs:
  release-please:
    runs-on: ubuntu-latest
    steps:
      - uses: googleapis/release-please-action@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          config-file: release-please-config.json
          manifest-file: .release-please-manifest.json
```

Release-please opens/updates a PR with:

- `CHANGELOG.md` updates (moves Unreleased into versioned section, opens new Unreleased).
- Version bump in `pyproject.toml` / `package.json` if configured.
- On merge: creates tag `vX.Y.Z` and GitHub Release.

### 3. Reconcile `.github/workflows/release.yml`

Current flow: manual tag push runs tests + `awk` changelog extract + gh release.

**Target flow:**

| Event | Action |
| --- | --- |
| release-please PR merged | Tag + GitHub Release created by release-please |
| Tag `v*.*.*` pushed | `release.yml` runs tests + Docker publish only |

Changes to `release.yml`:

1. Remove `Extract changelog entry` + `Create GitHub Release` steps (release-please handles).
2. Trigger on `release` event `types: [published]` OR keep `push: tags` for Docker only.
3. Keep backend tests, frontend build, Docker push jobs.

Example trigger:

```yaml
on:
  release:
    types: [published]
```

Pass `github.event.release.tag_name` to Docker tags.

### 4. CI changelog job adjustments

In `.github/workflows/ci.yml` `changelog` job:

- Keep `## [Unreleased]` check (release-please maintains it).
- Keep `check-changelog-sync.sh`.
- **Remove** warning-only empty Unreleased check for non-docs PRs (release-please fills it).
- Optional: fail if release-please PR is open and branch diverges (stretch).

### 5. Contributor workflow docs

Update:

- `CONTRIBUTING.md`: remove "you must edit CHANGELOG.md for every PR"; replace with
  "write conventional commits; release-please aggregates".
- `docs/operations/changelog-automation.md`: mark target workflow as shipped.
- `RELEASE_CHECKLIST.md`:
  - Remove manual "move Unreleased to version section".
  - Add "merge release-please PR" step.
  - Keep Docker and test gates.

### 6. Marketing and docs (no code changes expected)

Verify after first automated release:

- `/changelog` renders new version (ISR or redeploy).
- `bash scripts/check-changelog-sync.sh` passes.
- `docs/reference/changelog.md` regenerated in `prebuild`.

Optional: add release-please badge or "Last updated from git" footnote on changelog page
(out of scope unless trivial).

### 7. Tests

`tests/community/test_release_please_config.py`:

- Assert manifest JSON parses.
- Assert manifest version matches latest `## [x.y.z]` in `CHANGELOG.md` (excluding Unreleased).

`tests/community/test_changelog_workflow.py`:

- Sample `CHANGELOG.md` fixture with Unreleased + one release still parses.

## Migration (one-time, document in PR)

1. Ensure `CHANGELOG.md` `[Unreleased]` reflects commits since `0.1.0`.
2. Set `.release-please-manifest.json` to `0.1.0`.
3. Merge Prompt 166.
4. Let release-please open first release PR; review changelog text.
5. Merge to publish `v0.2.0` (or next semver as appropriate).

## Acceptance criteria

- [ ] `release-please-config.json` and manifest committed.
- [ ] `release-please.yml` opens release PRs on conventional commits to `main`.
- [ ] Merging release PR creates tag + GitHub Release without manual `awk` step.
- [ ] `release.yml` retained for test + Docker publish on published release.
- [ ] CONTRIBUTING, RELEASE_CHECKLIST, and `docs/operations/changelog-automation.md` updated.
- [ ] Manual Unreleased editing no longer required for routine PRs.
- [ ] `scripts/changelog-preview.sh` (Prompt 165) still works for pre-merge review.
- [ ] CI green; changelog sync check passes.

## Verification

1. Merge a `feat(scope): ...` commit to main.
2. Confirm release-please PR appears within one workflow run.
3. Review PR changelog body matches git-cliff preview (roughly).
4. Merge release PR; confirm tag and GitHub Release exist.
5. Deploy frontend; confirm `/changelog` shows new version.
6. Confirm Docker images publish from `release.yml`.

## Rollback

If release-please is too noisy pre-1.0:

- Disable `release-please.yml`.
- Revert to manual changelog + tag workflow in `release.yml`.
- Keep Prompt 164 commitlint and Prompt 165 preview.
