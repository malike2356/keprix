# keprix - Prompt 35: Community Infrastructure and Contribution Guide

## Purpose

Open source without community infrastructure is a repo nobody knows how to enter.
This prompt builds the GitHub-side infrastructure that makes it safe and easy for
contributors to participate and for maintainers to manage the project efficiently.

## GitHub Repository Files

All files below live at the root of `malike2356/keprix`.

### README.md (root level)

Already defined in Prompt 00. Ensure it includes:
- Badges: build status, latest release, license, Discord (when available).
- Links to: quickstart, full docs, feature comparison, contributing guide.
- The one-command install.
- License and attribution.

### CONTRIBUTING.md

`CONTRIBUTING.md` at the repo root.

Structure:
1. Before you start: check existing issues before opening a new one.
2. Development environment setup (Docker path, bare metal path).
3. Code standards: Python type hints required, no shell=True, follow engineering pillars.
4. Test requirements: every PR must include tests for new behavior.
5. Commit message format: `type(scope): short description` (conventional commits).
6. PR process: open a draft early, link to the issue, request review when ready.
7. Review turnaround: maintainers will review within 5 business days.
8. For large features: open a discussion in GitHub Discussions first.
9. Security issues: do not open a public issue. See SECURITY.md.
10. Code of Conduct: link to CODE_OF_CONDUCT.md.

### SECURITY.md

`SECURITY.md` at the repo root.

Content:
- Supported versions (latest release only).
- How to report a vulnerability:
  - Email: security@carinaai.uk (or the developer's contact).
  - Response time: acknowledge within 48 hours, provide timeline within 7 days.
  - Disclosure policy: 90-day coordinated disclosure.
- What to include in a report: description, steps to reproduce, impact, suggested fix.
- What NOT to do: do not open a GitHub issue for security vulnerabilities.
- Bug bounty: none currently. Credited in the release notes and ACKNOWLEDGMENTS.md.

### ACKNOWLEDGMENTS.md

Credits for:
- Hermes Agent, OpenClaw, Odysseus (with their licenses).
- All open-source libraries used in the project.
- Security researchers who reported vulnerabilities.
- Significant community contributors.

### CHANGELOG.md

Follows Keep a Changelog format. Updated with every release.

```markdown
# Changelog

## [Unreleased]

## [0.1.0] - YYYY-MM-DD
### Added
- Initial release.
- Core agent engine.
- Workspace (documents, notes, calendar).
...
```

The CI pipeline must verify that CHANGELOG.md is updated for every PR (CI check: does the
Unreleased section have content?).

## GitHub Issue Templates

`/.github/ISSUE_TEMPLATE/`

### bug_report.yml

Fields:
- Bug description (required).
- Steps to reproduce (required).
- Expected behavior (required).
- Actual behavior (required).
- keprix version (`keprix status` output) (required).
- OS and Docker version (required).
- Relevant logs (optional, collapsible).
- Checklist: "I have searched existing issues", "I have read the troubleshooting guide".

### feature_request.yml

Fields:
- Problem this feature solves (required, 2+ sentences).
- Proposed solution (required).
- Alternatives considered (optional).
- Is this a regression from a previous version? (checkbox).
- Checklist: "I have searched existing feature requests".

### security_report.yml

Content: a single message directing the reporter to SECURITY.md. Does not collect any
information publicly. This prevents security issues from being filed as regular issues.

### skill_pack_submission.yml

Fields:
- Pack name (required).
- What the pack does (required).
- GitHub repo or attachment (required).
- Category (dropdown: productivity, research, cyber, communication, data, other).
- Has a README: checkbox.
- Has tests: checkbox.
- Remote licence key required: no (keprix has none).

### question.yml

For usage questions. Reminds users that GitHub Discussions is preferred for questions.
Fields: what are you trying to do, what have you tried.

## GitHub PR Template

`.github/PULL_REQUEST_TEMPLATE.md`

```markdown
## Summary

Brief description of the change.

## Type

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor
- [ ] Documentation
- [ ] Security fix

## Related issue

Closes #

## Checklist

- [ ] Tests included and passing
- [ ] No `shell=True` in subprocess calls
- [ ] No credentials in the diff
- [ ] CHANGELOG.md updated (Unreleased section)
- [ ] Documentation updated if behavior changed
- [ ] Engineering pillars followed (no emojis, no em dashes, no forbidden typography)
```

## GitHub Actions Workflows

`.github/workflows/`

### ci.yml

Runs on every PR and push to main:
1. `uv sync` and run backend tests (`pytest tests/ -v`).
2. `pnpm install` and run frontend tests (`pnpm test`).
3. `scripts/audit-deps.sh` (from Prompt 02).
4. Secret scan: `gitleaks detect --no-git --source .` (ensures no credentials in diff).
5. Lint: `ruff check` (Python), `eslint` (TypeScript).
6. Type check: `mypy backend/` (Python), `tsc --noEmit` (TypeScript).
7. Check CHANGELOG.md has Unreleased content (warn, do not fail on docs-only PRs).

### release.yml

Triggered on push of a tag `v*.*.*`:
1. Run full test suite.
2. Build Docker images: `keprix-backend:{tag}` and `keprix-frontend:{tag}`.
3. Push images to Docker Hub (`carinaai/keprix-backend`, `carinaai/keprix-frontend`).
4. Create GitHub Release with the CHANGELOG.md entry for this version as the body.
5. Update `latest` Docker tag.
6. Trigger docs deployment (see docs.yml in Prompt 24).

### docs.yml

Triggered on push to main when `docs/` changes:
1. Run `scripts/generate-docs.sh`.
2. Run `mkdocs build`.
3. Deploy `site/` to GitHub Pages.

### stale.yml

Labels issues and PRs as stale after 60 days of no activity and closes them after 14 more
days. Exclude issues with `pinned` or `security` labels from going stale.

## GitHub Labels

Define a standard label set:

| Label | Color | Description |
| --- | --- | --- |
| `bug` | Red | Something is broken. |
| `feature` | Blue | New capability. |
| `security` | Dark red | Security-related. |
| `documentation` | Light blue | Docs change. |
| `good-first-issue` | Green | Suitable for newcomers. |
| `help-wanted` | Yellow | Maintainer wants community input. |
| `cyber` | Dark purple | Cyber module. |
| `aiva-key` | Purple | Related to feature gating. |
| `skill-pack` | Teal | Skill or plugin submission. |
| `pinned` | Gray | Do not go stale. |
| `wontfix` | White | Not going to be fixed. |
| `duplicate` | Light gray | Duplicate of another issue. |
| `needs-info` | Orange | Waiting for more info from the reporter. |

## GitHub Discussions

Enable GitHub Discussions with categories:
- Announcements (maintainer only): release notes, project updates.
- Q&A: usage questions. Best-answer marking enabled.
- Ideas: feature proposals before filing a feature request issue.
- Show and tell: users sharing what they built with keprix.
- Skill Packs: community pack sharing before formal submission.

## Community Onboarding

`docs/community/contributing.md` and `CONTRIBUTING.md` together form the onboarding path.
Additionally, a `good-first-issue` label is maintained on at least 5 open issues at all
times. These issues should be small, well-scoped, and have a clear acceptance criterion.

When a new issue is opened without a reproduction case, a bot (GitHub Actions) comments:
"Thanks for the report. Could you add a minimal reproduction case? See the bug report
template for guidance."

## Output Paths

```
.github/
  ISSUE_TEMPLATE/
    bug_report.yml
    feature_request.yml
    security_report.yml
    skill_pack_submission.yml
    question.yml
  PULL_REQUEST_TEMPLATE.md
  workflows/
    ci.yml
    release.yml
    docs.yml
    stale.yml

CONTRIBUTING.md
SECURITY.md
ACKNOWLEDGMENTS.md
CHANGELOG.md
CODE_OF_CONDUCT.md      - already present, verify it references SECURITY.md
```

## Tests

Community infrastructure does not have unit tests, but it has validation:

```
scripts/validate-community-files.sh
```

This script checks:
- CONTRIBUTING.md, SECURITY.md, ACKNOWLEDGMENTS.md, CHANGELOG.md all exist.
- CHANGELOG.md follows the Keep a Changelog format (has `## [Unreleased]` section).
- All issue templates are valid YAML.
- PULL_REQUEST_TEMPLATE.md includes the engineering pillars checklist item.
- No emoji appears in any of these files.

This script runs in CI on every PR.

## Acceptance Criteria

- All issue templates render correctly in GitHub's issue creation UI.
- The CI workflow runs on a test PR and passes all checks on a clean codebase.
- The release workflow produces a GitHub Release with correct CHANGELOG content.
- `scripts/validate-community-files.sh` passes.
- At least 5 issues are labeled `good-first-issue` with clear acceptance criteria.
- The stale workflow does not close issues labeled `pinned` or `security`.
- SECURITY.md contains a working contact email and a 48-hour response commitment.
- No emojis appear in any community file (CONTRIBUTING.md, SECURITY.md, PR template,
  issue templates, CHANGELOG.md).
