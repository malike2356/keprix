# FORGE Code Review Checklist

Use this checklist for every code review and patch submission.

## Security

- [ ] No hardcoded secrets, API keys, passwords, or tokens
- [ ] No credentials in comments or test fixtures
- [ ] Input validated at system boundaries
- [ ] Dependencies checked for known advisories

## Quality

- [ ] Type hints on all new Python functions and methods
- [ ] Strict TypeScript for new frontend code
- [ ] Tests added or updated for new functionality
- [ ] Lint passes without errors
- [ ] No dead code or commented-out blocks left behind

## Architecture

- [ ] Changes match existing project conventions
- [ ] Prefer composition over inheritance
- [ ] Scope is minimal; no unrelated refactors bundled in
- [ ] Error handling is explicit, not swallowed silently

## Approval

- [ ] Patch reviewed and approved before apply
- [ ] Sandbox mode `non-main` enforced for generation
- [ ] Host-level writes blocked without explicit approval

## Severity Levels

| Level | Action |
|-------|--------|
| critical | Block merge; fix secrets or security issues immediately |
| error | Block merge; fix before apply |
| warning | Note in review; fix or justify |
| info | Suggestion only |
