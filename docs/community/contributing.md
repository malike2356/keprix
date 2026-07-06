# Community contributing guide

This document extends [CONTRIBUTING.md](https://github.com/malike2356/keprix/blob/main/CONTRIBUTING.md) with onboarding
detail for new contributors.

## Repository map

| Path | Purpose |
| --- | --- |
| `src/keprix/` | Python backend, agent runtime, API routes |
| `frontend/` | Next.js workspace UI |
| `tests/` | Backend pytest suite |
| `docs/` | MkDocs documentation source |
| `scripts/` | Installer, audits, community validation |
| `docker/` | Container images for backend and frontend |

## First contribution workflow

1. Pick a `good-first-issue` or ask in Discussions if unsure where to start.
2. Comment on the issue so maintainers can assign or de-duplicate work.
3. Fork, branch, implement, and test locally.
4. Run `bash scripts/validate-community-files.sh` if you touch community files.
5. Open a draft PR and iterate from review feedback.

## Engineering pillars (required)

These apply to prose, comments, markdown, issue templates, and UI copy in this repo:

- No emojis.
- No em dashes or en dashes; use commas, colons, or hyphens instead.
- Prefer plain ASCII labels (`Done`, `Note:`, `WARNING:`).

Run `python3 scripts/fix-writing-style.py` from the repo root when editing
first-party markdown or UI strings.

## Pull request expectations

- Use a Conventional Commit **PR title** (`type(scope): description`); CI validates it.
- Include tests for behavioral changes.
- Write Conventional Commit messages; release-please aggregates changelog entries (no manual
  `CHANGELOG.md` edits for routine PRs).
- Update docs when user-visible behavior changes.
- Do not commit secrets, `.env` files, or credentials.

### Commit message format

Same as [CONTRIBUTING.md](https://github.com/malike2356/keprix/blob/main/CONTRIBUTING.md#commit-messages).
Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`,
`chore`, `revert`. Scopes such as `frontend`, `mutation`, and `api` are preferred.

Optional local validation from repo root:

```bash
pnpm install
echo "feat(docs): update contributing guide" | pnpm exec commitlint
```

Changelog automation details: [../operations/changelog-automation.md](../operations/changelog-automation.md).

Preview unreleased changelog from conventional commits:

```bash
bash scripts/changelog-preview.sh
```

## Where to ask questions

- **GitHub Discussions (Q&A):** usage questions and architecture ideas.
- **GitHub Issues:** reproducible bugs and scoped feature requests.
- **Security email:** vulnerability reports only.

See [discussions.md](discussions.md) for category guidance.

## Maintainer notes

- Keep at least five `good-first-issue` items open with clear acceptance criteria.
- Apply `pinned` or `security` labels to issues that must not go stale.
- Use `needs-info` when a bug report lacks reproduction steps.
