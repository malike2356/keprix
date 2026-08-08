# Keprix Prompt 334: Agent Parity Eval Suite

## Purpose

Create repeatable evals that compare Hermes-style agent behavior with Keprix behavior without relying on live paid models.

## Tasks

1. Add a parity eval suite under `evals/hermes_parity/` or `tests/parity/`.
2. Use fake providers and deterministic fixtures where possible.
3. Cover scenarios:
   - simple answer
   - tool call
   - multi-tool turn
   - failed tool recovery
   - file edit
   - terminal command
   - approval required
   - memory recall
   - skill-triggered behavior
   - provider retry
   - context compression
   - session resume
4. Add expected transcripts or structured assertions.
5. Add a command to run parity evals.

## Important

Do not require real API keys for the default parity suite.

Optional live-provider evals may exist, but they must be skipped by default unless env vars are present.

## Acceptance criteria

- The suite catches regressions in core behavior.
- The suite does not break when product modules are disabled.
- The suite has at least one test proving Keprix product hooks still work without altering core output unexpectedly.

## Verification

```bash
python -m pytest tests/parity -q
python -m pytest tests/agent tests/tools tests/memory -q
```
