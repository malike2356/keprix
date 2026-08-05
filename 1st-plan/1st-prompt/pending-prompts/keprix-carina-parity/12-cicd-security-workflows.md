# Prompt 415 / 12: CI/CD security workflows

Status: COMPLETED 2026-08-04
Series: Keprix close Carina parity gaps  
Depends on: 407 / 04  
Blocks: none (programme gate with others)  
Severity: LOW  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Carina has many GitHub Actions security/compliance workflows. Keprix deploy story is Docker/Fly-focused.

## Goal

Add a minimal but real GH Actions set for Keprix: lint/test, capability-mesh soft gate, dependency audit, secret scan (existing tools if any).

## Must-haves

1. Workflow YAML under `.github/workflows/` (or document why CE mirror differs).
2. Runs `pytest` subset + `check-capability-mesh.sh`.
3. Docs in ops/README pointer.

## Acceptance

- [x] Workflow validates on PR dry syntax.
- [x] Mesh soft gate invoked.
