# Contributing to Keprix

Thank you for helping improve Keprix. This file is the entry point for
contributors. Extended guidance lives in [docs/community/contributing.md](docs/community/contributing.md).

## Before you start

1. Search [existing issues](https://github.com/malike2356/keprix/issues) before opening a duplicate.
2. For large features, open a [GitHub Discussion](https://github.com/malike2356/keprix/discussions) first.
3. For security issues, read [SECURITY.md](SECURITY.md). Do not file public issues.

## Development environment

### Bare metal (recommended for day-to-day work)

```bash
git clone https://github.com/malike2356/keprix.git
cd keprix
bash scripts/install.sh
source .venv/bin/activate
cd frontend && pnpm install && cd ..
```

Run backend tests:

```bash
.venv/bin/python -m pytest tests/ -q
```

Run frontend checks:

```bash
cd frontend && pnpm lint && pnpm type-check && pnpm build
```

### Docker path

```bash
docker compose -f docker/docker-compose.yml up --build
```

Use Docker when you need an isolated environment close to production.

## Code standards

- Python 3.11+ with type hints on new code.
- No `shell=True` in `subprocess` calls.
- Follow engineering pillars: no emojis, no em dashes, no en dashes in project prose.
- Match existing module layout under `src/keprix/` and `frontend/src/`.
- Prefer focused diffs; avoid unrelated refactors in the same pull request.

## Tests

Every pull request that changes behavior must include or update tests in `tests/`
or frontend checks where UI behavior changes.

Workspace and admin pages must use skeleton primitives from
`frontend/src/components/ui/loading/` for primary data regions (not `Loading...`
text or page-level spinners). See `docs/frontend/loading-states.md` and
`tests/ui/test_loading_contract.py`.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/). CI enforces commit
messages and **PR titles** (required for squash merges).

```text
type(scope): short description
```

### Allowed types

`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

### Common scopes

`agent`, `mutation`, `billing`, `auth`, `frontend`, `api`, `cli`, `docker`, `docs`,
`research`, `memory`, `vault`, `mcp`, `playbook`, `evals`, `deps`

Unknown scopes produce a **warning** only; invalid types or malformed headers fail CI.

Examples:

- `fix(export): persist review artifact`
- `feat(legal): add acceptance gate`
- `chore(deps): bump axios`

Optional local check (after `pnpm install` at repo root):

```bash
echo "feat(frontend): my change" | pnpm exec commitlint
```

See [docs/operations/changelog-automation.md](docs/operations/changelog-automation.md) for
how commits feed the changelog pipeline. Preview unreleased entries from git:

```bash
bash scripts/changelog-preview.sh
```

## Pull request process

1. Open a draft pull request early when work is exploratory.
2. Link the related issue (`Closes #123`).
3. Complete the PR checklist, including Conventional Commit PR title.
4. Request review when CI is green and the diff is ready.

Changelog entries are aggregated by [release-please](https://github.com/googleapis/release-please)
from your Conventional Commit messages. You do **not** need to edit `CHANGELOG.md` for routine
PRs. Preview what will ship:

```bash
bash scripts/changelog-preview.sh
```

Maintainers merge the release-please PR when cutting a version. See
[docs/operations/changelog-automation.md](docs/operations/changelog-automation.md).

Maintainers aim to review within **5 business days**.

## Security and conduct

- Security reports: [SECURITY.md](SECURITY.md)
- Community standards: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## Good first issues

Look for the `good-first-issue` label. Maintainer seed list:
[docs/community/good-first-issues.md](docs/community/good-first-issues.md).
