# Changelog automation

How Keprix maintains `CHANGELOG.md`, the marketing `/changelog` page, and GitHub Releases.

## Source of truth

| Artifact | Path | Updated by |
| --- | --- | --- |
| Canonical changelog | `CHANGELOG.md` (repo root) | release-please (on release PR merge) |
| Version | `pyproject.toml` | release-please |
| MkDocs copy | `docs/reference/changelog.md` | `scripts/generate_doc_pages.py --only changelog` |
| Marketing page | `frontend/src/app/(marketing)/changelog/page.tsx` | Reads `CHANGELOG.md` at render (ISR: 5 min) |
| GitHub Release | GitHub Releases UI | release-please (on release PR merge) |
| Docker images | Docker Hub | `.github/workflows/release.yml` on `release: published` |

## Shipped workflow (Conventional Commits + release-please)

1. Contributor opens a PR with Conventional Commit title and commits (commitlint in CI).
2. Optional: review unreleased notes with `bash scripts/changelog-preview.sh` (git-cliff).
3. PR merges to `main`; no manual `CHANGELOG.md` edit required.
4. `.github/workflows/release-please.yml` opens or updates a **release PR** with:
   - Finalized version section in `CHANGELOG.md`
   - Fresh empty `## [Unreleased]`
   - `pyproject.toml` version bump
5. Maintainer reviews and merges the release PR.
6. release-please creates tag `vX.Y.Z` and GitHub Release.
7. `.github/workflows/release.yml` runs tests and publishes Docker images.
8. `frontend` `prebuild` regenerates `docs/reference/changelog.md`; deploy updates `/changelog`.

### How often the marketing page updates

| Environment | Behaviour |
| --- | --- |
| Local `pnpm dev` | Refreshes on browser reload when `CHANGELOG.md` changes |
| Production | After commit + deploy; ISR `revalidate = 300` re-reads file every 5 minutes |

The page does **not** poll GitHub. It only reads the `CHANGELOG.md` file on disk.

### Helper commands

```bash
# Sync docs copy only (no API app import)
python3 scripts/generate_doc_pages.py --docs-dir docs --only changelog

# Verify root and docs copy match
bash scripts/check-changelog-sync.sh

# Preview unreleased entries from conventional commits (git-cliff; read-only)
bash scripts/changelog-preview.sh

# Full changelog from git history (stdout only; review before any manual replace)
bash scripts/changelog-generate-full.sh
```

Install [git-cliff](https://git-cliff.org/) locally, or download the binary to `.tools/git-cliff`
(see `scripts/changelog-git-cliff.sh`). CI installs git-cliff v2.7.0 in
`.github/workflows/changelog-generate.yml`.

Configuration: `cliff.toml` at repo root. Commits matching `docs`, `chore`, `ci`, `build`,
`style`, and `test` are skipped in generated output.

## Tool roles

| Tool | Role |
| --- | --- |
| **commitlint** | Enforce Conventional Commits on PR commits and titles |
| **git-cliff** | Local preview and CI unreleased artifact (read-only) |
| **release-please** | Semver bumps, release PRs, `CHANGELOG.md` writer, tags, GitHub Releases |

**Do not run git-cliff and release-please as writers on main.** release-please owns versioned
sections; git-cliff is for preview and drift checks only.

### Conventional Commit to Keep a Changelog mapping

| Commit prefix | Changelog section |
| --- | --- |
| `feat` | Added |
| `fix` | Fixed |
| `perf` | Changed |
| `refactor` | Changed |
| `docs` | Changed (or skip in user-facing changelog) |
| `chore`, `ci`, `build` | Skip unless `chore(deps)` flagged |
| `BREAKING CHANGE` footer or `!` | Changed + breaking callout |

Scopes map to Keprix areas: `mutation`, `billing`, `frontend`, `auth`, `research`, etc.

### Contributor and maintainer checklist

**Contributors:**

- Write Conventional Commit messages; do not hand-edit Unreleased for routine changes.
- Use `bash scripts/changelog-preview.sh` to preview unreleased notes locally.

**Maintainers:**

- Merge the release-please PR to cut a release (tag + GitHub Release).
- Edit release PR changelog text only for major announcements or corrections.
- Review the release-please PR changelog against `bash scripts/changelog-preview.sh` before merging.

### First automated release (migration)

1. Ensure `CHANGELOG.md` `[Unreleased]` reflects commits since the last shipped version.
2. Confirm `.release-please-manifest.json` matches the latest `## [x.y.z]` in `CHANGELOG.md`.
3. Merge conventional commits to `main`; wait for the release-please PR.
4. Review changelog text against `bash scripts/changelog-preview.sh`.
5. Merge the release PR to publish the next semver tag.

### Related files

- `release-please-config.json`, `.release-please-manifest.json`
- `.github/workflows/release-please.yml`, `.github/workflows/release.yml`
- `frontend/src/lib/changelog.ts` parser (Keep a Changelog headings)
- `scripts/generate_doc_pages.py` (`write_changelog`)
- `scripts/check-changelog-sync.sh`
- `.github/workflows/ci.yml` (`changelog` job)
- `.github/workflows/changelog-generate.yml` (PR preview artifact)
- `.github/workflows/docs.yml` (triggers on `CHANGELOG.md`)

### Marketing note

The `/changelog` UI requires no changes; it already parses `CHANGELOG.md`. release-please
output must keep Keep a Changelog headings:

```markdown
## [Unreleased]

### Added
- ...

## [1.2.0] - 2026-07-06
```
