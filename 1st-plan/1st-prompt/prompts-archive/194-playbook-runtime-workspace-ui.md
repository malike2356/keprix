# Keprix - Prompt 194: Playbook Runtime Workspace UI (Prompt 51 Product Surface)

**Status:** Completed 2026-07-06. Tests: `tests/playbook/test_runtime_*.py` (29 passed).

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Durable playbook runtime | `src/keprix/playbook/runtime/` |
| Run HTTP API (start/get/events/resume/pause) | `src/keprix/playbook/run_routes.py` (`/api/playbook-runs/*`) |
| Runtime tests | `tests/playbook/test_runtime_*.py` |
| Hardware/model helpers in frontend | `frontend/src/lib/playbook-api.ts` (scan, models, serve) |
| Docs | `docs/keprix-playbook-runtime.md` |

## Gap

`/playbooks` is still link cards only. No UI for start, inspect, pause, resume, or event timeline.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Reference

- Archived: `51-langgraph-style-durable-playbook-runtime.md`
- Backend: `src/keprix/playbook/run_routes.py`, `playbook/runtime/runner.py`
- Docs: `docs/keprix-playbook-runtime.md`

## Step 1: API client

Extend `frontend/src/lib/playbook-api.ts` (keep existing hardware/model helpers):

```typescript
export type PlaybookRun = {
  run_id: string;
  graph_id: string;
  workspace_id: string;
  status: "pending" | "running" | "paused" | "interrupted" | "completed" | "failed";
  state: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
};

export async function startPlaybookRun(body: {
  graph_id: string;
  workspace_id?: string;
  initial_state?: Record<string, unknown>;
  steps?: Array<Record<string, unknown>>;
  edges?: Array<Record<string, unknown>>;
  entry?: string;
}): Promise<PlaybookRun>;

export async function fetchPlaybookRun(runId: string): Promise<PlaybookRun>;
export async function fetchPlaybookRunEvents(runId: string): Promise<{ events: PlaybookEvent[] }>;
export async function resumePlaybookRun(runId: string, patch?: Record<string, unknown>): Promise<PlaybookRun>;
export async function pausePlaybookRun(runId: string): Promise<PlaybookRun>;
export async function cancelPlaybookRun(runId: string): Promise<PlaybookRun>;
```

Base path: `/api/playbook-runs` via `ceApi`.

## Step 2: Playbooks list page

Replace `frontend/src/app/(workspace)/playbooks/page.tsx`:

| Section | Behavior |
| --- | --- |
| Header | Title "Playbooks", CTA "Start run" |
| Templates | Cards for built-in graphs: `sdk-workflow`, `research-deep-dive`, `opportunity-scan` (load from `GET /api/playbook/graphs` or static catalog in `playbook/routes.py`) |
| Recent runs | Table: run_id, graph_id, status chip, updated_at, link to detail |
| Empty state | Link to `examples/borehole-ghana/playbook.yaml` |

Use `SkeletonTable` while loading; `EmptyState` when no runs.

## Step 3: Run detail page

Create `frontend/src/app/(workspace)/playbooks/[runId]/page.tsx`:

1. Poll `fetchPlaybookRun` every 2s while `status` is `running` or `paused`
2. Event timeline from `fetchPlaybookRunEvents` (node start, node end, interrupt, error)
3. State inspector (collapsible JSON, read-only)
4. Actions: Pause, Resume (dialog if `interrupted` needs approval payload), Cancel
5. Human interrupt banner when `status === "interrupted"` with Approve / Reject calling resume with `approved_by`

## Step 4: Start run dialog

Component `frontend/src/components/playbooks/StartPlaybookDialog.tsx`:

- Pick template or paste YAML (optional advanced tab)
- `initial_state` JSON editor with validation
- On submit: `startPlaybookRun` then `router.push(/playbooks/{run_id})`

## Step 5: Backend list endpoint (if missing)

Add to `playbook/run_routes.py`:

```python
@router.get("")
async def list_playbook_runs(workspace_id: str = "default", limit: int = 50) -> dict:
    ...
```

Index from `playbook_registry` in memory; document persistence limits.

## Step 6: Navigation

Ensure `frontend/src/lib/navigation.ts` Playbooks entry has badge when any run is `interrupted`.

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | `/playbooks` lists templates and recent runs (not link cards only) |
| 2 | Start `sdk-workflow` from UI; detail page shows event stream |
| 3 | Pause and resume work from UI |
| 4 | Interrupted run shows approval UI and resumes on approve |
| 5 | `cd frontend && pnpm exec tsc --noEmit` passes |
| 6 | `pytest tests/playbook/test_runtime_*.py` still passes |
| 7 | Operator copy uses "playbook" not "recipe" |

## Archive

`prompts-archive/` when AC pass.
