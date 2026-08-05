# Prompt: Adopt Trigger Builder For Keprix Playbooks

## Goal

Unify Keprix playbooks, action board, cron jobs, and automations behind a user-facing trigger builder.

## Source Research

Reference only:

- `/opt/lampp/htdocs/verlox/keprix/1st-plan/competitor-research/00-agents-to-adopt/myapi-open/src/lib/triggerEngine.js`
- `/opt/lampp/htdocs/verlox/keprix/1st-plan/competitor-research/00-agents-to-adopt/myapi-open/docs/TRIGGERS_SPEC.md`

Do not copy AGPL code. Reimplement the behavior.

## Required Behavior

- Support schedule triggers: interval, daily, weekly, monthly, cron, and once where useful.
- Support event triggers from connectors, webhooks, run-ledger events, repository events, and workspace events.
- Support actions: run playbook, call tool, ask agent, run mutation, create task, call webhook, or request approval.
- Queue due runs so execution does not require a browser session.
- Use a lease or equivalent lock so concurrent workers do not double-run.
- Record run history, result, cost, quota impact, approval status, and linked artifacts.
- Route LLM calls through BYOK or managed wallet enforcement.
- Risky actions must respect tool ACLs, approvals, quotas, and audit.

## Implementation Targets To Inspect

- `docs/features/playbooks.md`
- `docs/features/agent-os-action-board.md`
- `docs/features/cron-jobs.md`
- `docs/features/agent-os-run-ledger.md`
- `src`
- `web`
- Existing playbook, action board, scheduler, and worker modules.

## Implementation Steps

1. Map current playbook, cron, and action-board concepts.
2. Define a trigger schema that wraps existing behavior.
3. Add scheduler tick and queued run worker.
4. Add action dispatcher for playbooks, tools, agents, mutation runs, and webhooks.
5. Add approval policy for side-effect actions.
6. Add UI for trigger, condition, action, approval mode, test run, and history.
7. Add run-ledger integration.
8. Update Keprix self-knowledge docs so the assistant can explain automations.

## Tests

- Scheduled trigger queues one run when due.
- Worker lease prevents duplicate execution.
- Triggered playbook writes run-ledger entry.
- Risky tool action waits for approval.
- Quotas and wallet enforcement apply to triggered runs.

## Done Criteria

- Users can create automations without touching cron config.
- Existing playbooks become more discoverable.
- Triggered runs are auditable and cost-aware.
- No AGPL code is copied.
