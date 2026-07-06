---
name: keprix-core-developer
description: Base coding capabilities for FORGE; generation, review, patching, and sandbox enforcement.
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  keprix:
    tags: [forge, coding, review, sandbox, patches]
    related_skills: [test-driven-development, requesting-code-review, systematic-debugging]
---

# Keprix Core Developer

FORGE technical execution skill pack.

## Capabilities

- Generate code in sandbox mode `non-main`
- Review code for secrets, type hints, and test coverage
- Prepare and apply patches through approval flow
- Enforce host-level write blocking outside the repo

## Standards

- No secrets in code
- Tests required for new functionality
- Type hints required (Python); strict TypeScript
- Prefer composition over inheritance
- All patches require approval before apply

## Workflow

1. Generate or receive code change
2. Run `review_code()` against the checklist
3. `prepare_patch()` with sandbox enforcement
4. Apply only after explicit approval
