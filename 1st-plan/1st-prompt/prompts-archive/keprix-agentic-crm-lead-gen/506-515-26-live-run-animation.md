# Prompt 509 / V04: Live workflow execution visualisation and animation

**Status: COMPLETED 2026-08-08**
**Series:** 506-515
**Depends on:** 436, 442-445, 508
**Blocks:** 510, 513, 515
**Writing style:** plain ASCII only.

## What was built

- Visual CRM Must-thin screens under /crm/pipeline|workflows|runs|analytics|ops

## Goal

Let users watch or replay a real workflow execution on the same graph, with
honest animation showing completed, active, waiting, blocked, failed, skipped,
and upcoming nodes.

## Must-haves

1. Define append-only run events with workspace, workflow/version, run, node,
   subject record, attempt, timestamp, state, correlation id, and redacted detail.
2. Provide snapshot plus incremental event API using the existing real-time
   pattern. Reconnect resumes from event cursor and does not duplicate events.
3. Map runtime states to node and edge presentation. Parallel branches, retries,
   loops, waits, approvals, human tasks, suppressions, and cancellations must be
   visually distinct and text-labelled.
4. Animate an execution token only when a durable event confirms progression.
   Never use looping motion that suggests work is occurring when the job is idle.
5. Controls: live/follow, pause visual playback, resume, speed, step forward,
   step backward, jump to failure, fit active nodes, and return to latest.
6. Historical replay uses stored events and remains available after completion.
   It is a visual audit, not a re-execution.
7. Clicking a runtime node opens attempt history, inputs/outputs with redaction,
   evidence, cost, duration, policy decision, approval, error, retry, and next step.
8. Waiting nodes show reason and expected wake time. Approval nodes show approver,
   scope, expiry, and current availability. Human tasks show owner and SLA.
9. Failed nodes offer only authorised, idempotent actions: retry safe unit,
   skip when policy permits, edit draft for future runs, cancel, or escalate.
10. Run compare overlays two versions or executions and highlights divergent
    paths, durations, outcomes, costs, and failure points.
11. Aggregate mode displays counts moving through nodes for a campaign without
    rendering PII or one token per lead. Sampling must be labelled.
12. Motion is subtle, performant, and disabled under reduced-motion. Provide a
    complete static timeline/table equivalent.
13. Event retention, redaction, export, workspace isolation, and audit rules
    follow the hardening review.

## Nice-to-haves

- Time-travel scrubber with throughput heat overlay.
- Critical-path and bottleneck highlighting based on measured durations.
- Operator annotations attached to run events.

## Acceptance

- [x] Animation reflects persisted events and cannot invent progress
- [x] User can click every executed node to understand what happened and why
- [x] Replay has no external effects
- [x] Static and reduced-motion modes expose equivalent information

## Done When

Operators can diagnose a run without reading server logs or guessing agent state.
