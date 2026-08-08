# Contributing to Keprix

Thank you for helping improve Keprix. This file is the short entry point.
Extended guidance: [docs/community/contributing.md](docs/community/contributing.md).

## Before you start

1. Search [existing issues](https://github.com/malike2356/keprix/issues) before opening a duplicate.
2. For large features, open a [GitHub Discussion](https://github.com/malike2356/keprix/discussions) first.
3. For security issues, read [SECURITY.md](SECURITY.md). Do not file public issues.

## Development environment

Fork the repo, then:

```bash
git clone https://github.com/<your-fork>/keprix.git
cd keprix
bash scripts/install.sh
source .venv/bin/activate
# or use uv if you prefer; see docs/community/contributing.md
cd frontend && pnpm install && cd ..
```

Backend tests:

```bash
.venv/bin/python -m pytest tests/ -q
```

Frontend checks:

```bash
cd frontend && pnpm lint && pnpm type-check && pnpm build
```

Docker (isolated stack closer to production):

```bash
docker compose -f docker/docker-compose.yml up --build
```

## Code standards

- Python 3.11+ with type hints on new code.
- No `shell=True` in `subprocess` calls.
- Plain ASCII in project prose: no emojis, no em dashes, no en dashes.
- Match existing layout under `src/keprix/` and `frontend/src/`.
- Prefer focused diffs; avoid unrelated refactors in the same pull request.

## Tests

PRs that change behavior must include or update tests in `tests/` or frontend
checks where UI behavior changes. Workspace loading contracts:
[docs/frontend/loading-states.md](docs/frontend/loading-states.md).

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/). CI enforces
commit messages and **PR titles** (required for squash merges).

```text
type(scope): short description
```

Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
`build`, `ci`, `chore`, `revert`.

Common scopes: `agent`, `mutation`, `billing`, `auth`, `frontend`, `api`,
`cli`, `docker`, `docs`, `memory`, `vault`, `mcp`, `playbook`, `evals`, `deps`.

Examples: `fix(export): persist review artifact`, `feat(cli): improve setup wizard`.

Optional local check (after `pnpm install` at repo root):

```bash
echo "feat(frontend): my change" | pnpm exec commitlint
```

Changelog preview: `bash scripts/changelog-preview.sh`. Details:
[docs/operations/changelog-automation.md](docs/operations/changelog-automation.md).

## Pull request process

1. Open a draft PR early when work is exploratory.
2. Link the related issue (`Closes #123`).
3. Use a Conventional Commit PR title; keep the diff reviewable.
4. Request review when CI is green.

Maintainers merge release-please PRs when cutting a version. Aim: review within
**5 business days**.

## Public releases and archives

Workspace planning under `1st-plan/` is maintainer-local. `.gitattributes`
marks `1st-plan/`, `AGENTS.md`, and `CLAUDE.md` as `export-ignore` for source
archives. Product paths `src/`, `frontend/`, `docker/`, and `docs/` ship
normally.

Before making the GitHub repository public, follow
[docs/operations/public-github-checklist.md](docs/operations/public-github-checklist.md).

## Security and conduct

- Security reports: [SECURITY.md](SECURITY.md)
- Community standards: [docs/community/code-of-conduct.md](docs/community/code-of-conduct.md)

## Good first issues

Look for the `good-first-issue` label. Maintainer seed list:
[docs/community/good-first-issues.md](docs/community/good-first-issues.md).
