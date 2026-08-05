# Keprix Prompt 332: File Terminal Approval and Safety Parity

## Purpose

Match Hermes behavior for file edits, terminal execution, approval prompts, sandboxing, and safety UX while preserving Keprix security defenses and product ACLs.

## Preconditions

Complete Prompt 327 inventory first.

## Tasks

1. Compare Hermes and Keprix:
   - file read/write/edit flow
   - patch application
   - terminal command execution
   - long-running command handling
   - approval prompts
   - denied command handling
   - sandbox policy
   - output truncation
   - audit events
2. Port missing Hermes behavior where it improves operator trust.
3. Preserve Keprix additions:
   - terminal sandbox policy
   - file/network gates
   - product ACL
   - Scout signal emission
   - Channel Shield and output guards
4. Add tests for approval and denial paths.

## Acceptance criteria

- File edit flow is predictable and test-covered.
- Terminal execution has clear policy outcomes.
- Approval prompts work in CLI and TUI where supported.
- Keprix security remains stricter where intentionally better than Hermes.

## Verification

```bash
python -m pytest tests/security tests/tools tests/tui tests/agent -q
python -m pytest tests/architecture -q
```
