# Keprix - Prompt 209: Playbook Run Step I/O Detail (n8n Execution Parity)

## Purpose

Close gap **P2** (#15 in capability matrix) from `planning/competitor-research/agents-to-adopt/n8n/GAPS-FOR-KEPRIX.md`.
n8n execution view shows per-node input/output JSON. Keprix emits `input_state` / `output_state` in
`NODE_STARTED` / `NODE_COMPLETED` events but `/playbooks/[runId]` does not surface them clearly.

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Event emitter with node I/O | `src/keprix/playbook/runtime/runner.py` (lines 109-130) |
| Events API | `GET /api/playbook-runs/{id}/events` in `run_routes.py` |
| Run detail page | `frontend/src/app/(workspace)/playbooks/[runId]/page.tsx` |
| Event types | `src/keprix/playbook/runtime/events.py` |

## Gap

Run detail timeline lists events but operators cannot inspect per-step input/output like n8n execution data panel.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Step 1: Normalize event payloads (backend)

Ensure every `NODE_COMPLETED` payload includes:

```python
{
  "node": "step_id",
  "input_state": {...},   # snapshot at node start
  "output_state": {...},  # full state after node (or delta key `output` if large)
  "duration_ms": 123,
}
```

If `NODE_STARTED` already carries `state`, duplicate as `input_state` in `NODE_COMPLETED` for UI convenience (small graphs only; truncate values > 32KB with `{ "_truncated": true, "preview": "..." }`).

Add helper `src/keprix/playbook/runtime/event_payload.py` with `truncate_state(state, max_bytes=32768)`.

Update `tests/playbook/test_runtime_events.py` (or add) to assert I/O keys exist.

## Step 2: Step timeline component

Create `frontend/src/components/playbooks/PlaybookStepTimeline.tsx`:

| UI element | Behavior |
| --- | --- |
| Vertical timeline | One row per node execution (merge STARTED+COMPLETED pairs) |
| Status chip | success / failed / interrupted / pending |
| Expand row | Shows tabs: Input JSON, Output JSON, Raw events |
| Copy button | Copy JSON to clipboard |
| Duration | From `duration_ms` when present |

Use `CodeBlock` or `MarkdownRenderer` JSON fence; redact keys matching `*password*`, `*token*`, `*secret*` (client-side mask).

## Step 3: Wire run detail page

Replace flat `List` of events in `[runId]/page.tsx`:

- Top: existing status banner, actions (pause/resume/cancel)
- Middle: `PlaybookStepTimeline` built from `events` SWR data
- Bottom: collapsible full state inspector (keep existing)

Poll unchanged (2s while running).

## Step 4: API client types

Extend `frontend/src/lib/playbook-api.ts`:

```typescript
export type PlaybookNodeEvent = {
  event_type: string;
  timestamp: string;
  payload: {
    node?: string;
    input_state?: Record<string, unknown>;
    output_state?: Record<string, unknown>;
    duration_ms?: number;
    error?: string;
  };
};
```

Add `groupPlaybookEventsByNode(events): StepRunRow[]` pure function + unit test in `playbook-api.test.ts` if test harness exists, else `*.test.ts` colocated.

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | Completed node events include `input_state` and `output_state` (or truncated preview) |
| 2 | `/playbooks/{runId}` shows expandable per-step I/O for `sdk-workflow` test run |
| 3 | Secrets redacted in UI display |
| 4 | `pytest tests/playbook/test_runtime_*.py` still passes |
| 5 | Failed node shows error payload in timeline row |

## Archive

`prompts-archive/` when AC pass.
