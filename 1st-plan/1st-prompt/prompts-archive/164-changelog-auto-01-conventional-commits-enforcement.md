# Keprix Prompt 164: Changelog automation 01 - Conventional Commits enforcement

## Purpose

Make Conventional Commits **machine-enforceable** so git-cliff and release-please can
generate `CHANGELOG.md` without hand-written bullets.

Depends on reference **163** (`prompts-archive/ref-163-changelog-automation-architecture.md`).
Read `docs/operations/changelog-automation.md`.

**Out of scope:** Generating changelog text (Prompt 165). Release PRs (Prompt 166).

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## What to build

### 1. Root `commitlint.config.js`

Use `@commitlint/config-conventional` with Keprix scopes:

```javascript
/** @type {import('@commitlint/types').UserConfig} */
module.exports = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "type-enum": [
      2,
      "always",
      ["feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore", "revert"],
    ],
    "scope-enum": [
      1,
      "always",
      [
        "agent", "mutation", "billing", "auth", "frontend", "api", "cli", "docker",
        "docs", "research", "memory", "vault", "mcp", "playbook", "evals", "deps",
      ],
    ],
    "subject-case": [2, "never", ["start-case", "pascal-case", "upper-case"]],
    "header-max-length": [2, "always", 100],
  },
};
```

Scope rule severity `1` = warn (do not block drive-by fixes outside listed scopes).

### 2. Dev dependencies

In repo root `package.json` (create minimal root package.json if missing, or use
`frontend/package.json` only if monorepo pattern already exists; prefer **root**
`package.json` with `"private": true` for shared tooling):

```json
{
  "private": true,
  "devDependencies": {
    "@commitlint/cli": "^19.8.0",
    "@commitlint/config-conventional": "^19.8.0"
  },
  "scripts": {
    "commitlint": "commitlint --edit"
  }
}
```

Add lockfile (`pnpm-lock.yaml` at root) or document `npm install` in CONTRIBUTING.

Optional: Husky hook `.husky/commit-msg` calling `pnpm commitlint` (document opt-in
install; do not require husky for CI-only enforcement).

### 3. CI: validate PR titles and commits

Add `.github/workflows/commitlint.yml`:

```yaml
name: Commitlint

on:
  pull_request:
    types: [opened, edited, synchronize, reopened]

permissions:
  contents: read

jobs:
  commitlint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: pnpm/action-setup@v4
        with:
          version: 9
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: pnpm install --frozen-lockfile
      - uses: wagoid/commitlint-github-action@v6
        with:
          configFile: commitlint.config.js
```

Also validate **PR title** matches conventional format (squash merges use PR title):

```yaml
      - name: PR title lint
        env:
          PR_TITLE: ${{ github.event.pull_request.title }}
        run: |
          echo "$PR_TITLE" | pnpm exec commitlint
```

### 4. Documentation updates

**`CONTRIBUTING.md`** section "Commit messages":

- List allowed types and example scopes.
- Note PR title must be conventional if using squash merge.
- Link to `docs/operations/changelog-automation.md`.

**`docs/community/contributing.md`**: mirror the same section.

**`.github/PULL_REQUEST_TEMPLATE.md`**: add checklist item:

```markdown
- [ ] PR title follows Conventional Commits (`type(scope): description`)
```

### 5. Tests

`tests/community/test_commitlint_config.py` (lightweight):

- Assert `commitlint.config.js` exists.
- Assert required types include `feat` and `fix`.
- Optional: shell out to `pnpm exec commitlint` with good/bad messages if node available in CI backend job (skip if not installed).

## Acceptance criteria

- [ ] `commitlint.config.js` at repo root with Keprix scopes.
- [ ] CI workflow fails PRs with non-conventional commit messages or PR titles.
- [ ] CONTRIBUTING and community docs updated with enforcement rules.
- [ ] PR template checklist includes conventional title.
- [ ] Existing contributors can use `feat`, `fix`, `chore`, etc. without new local setup (CI is the gate).
- [ ] No change to `CHANGELOG.md` workflow yet (manual Unreleased still valid until Prompt 166).

## Verification

```bash
echo "bad commit" | pnpm exec commitlint   # fails
echo "feat(frontend): add changelog hero" | pnpm exec commitlint   # passes
```

Open test PR with title `update stuff` (should fail) and `feat(docs): changelog automation` (should pass).
