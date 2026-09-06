# Mutation Parity Audit

**Date:** 2026-09-02
**Scope:** Keprix mutation subsystem compared with the Prime Continual Harness contract described by prompt 061.
**Status:** Partial: the Prime reference source is not present at the declared checkout path.

## Evidence Matrix

| Capability | Prime evidence | Keprix evidence | Verdict |
| --- | --- | --- | --- |
| Harness state persistence | Declared JSON harness state; source unavailable locally | `mutation/store.py`, `mutation_events` SQLite/PostgreSQL persistence | Keprix implementation verified; Prime comparison pending |
| Tiers | Declared prompt, memory, skill, and subagent kinds; source unavailable locally | `MutationStore.save_mutation_event()` and tier-specific routes for tool, prompt, persona, and code | Keprix implementation verified; Prime comparison pending |
| Approval gate | No local Prime source to verify | `mutation/store.py`, approval fields, staged records, and mutation routes | Keprix governance path verified |
| Quality scoring | No local Prime source to verify | `mutation/quality.py`, quality samples, and compounding metrics | Keprix implementation verified |
| Retention and pruning | No local Prime source to verify | `mutation/retention.py`, `mutation/pruner.py`, and prune route | Keprix implementation verified |
| Self-coding | Host-side capability in declared contract; source unavailable locally | `mutation/self_coding_harness.py`, `self_coding_scope.py`, `self_coding_git.py`, and `tool_sandbox.py` | Keprix implementation verified |
| Tool synthesis | No local Prime source to verify | `mutation/tool_synthesizer.py` and mutation routes | Keprix implementation verified |
| Refinement events | Declared as recorded; source unavailable locally | No verified dedicated refinement tier or trigger found in the local mutation module | Gap decision blocked on Prime source and product semantics |
| Subagent-spec mutation | Declared as recorded; source unavailable locally | `tools/delegate_tool.py` provides delegation, but no verified subagent-spec mutation path was found | Gap decision blocked on Prime source and product semantics |

## Verification

The existing mutation tests cover the approval, persistence, rollback, quality,
pruning, self-coding scope, and route surfaces. No schema change was made by
this audit. The two candidate gaps were not filled because their required
Prime behavior and the intended Keprix representation cannot be verified
without the missing reference source.

## Follow-up

Restore `reference-projects/prime-agent/prime-agent-runtime/src/rlm/harness.py`
or provide an equivalent pinned reference, then rerun this matrix. If
refinement events or subagent-spec mutation are confirmed as required, reuse
`mutation_events` and the existing approval and rollback paths.
