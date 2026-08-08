# Keprix - Prompt 198: Builder Trajectory UI Gaps (Prompts 55, 153)

**Status:** Completed 2026-07-06. Tests: `test_job_trajectory`, `test_trajectory`, `test_builder`.

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Builder project list + start job | `frontend/src/app/(workspace)/builder/page.tsx` |
| Job detail + log stream | `frontend/src/app/(workspace)/builder/jobs/[id]/page.tsx` |
| Builder API | `frontend/src/lib/builder-api.ts` |
| JSONL trajectory backend | `src/keprix/coding/trajectory.py`, `coding/routes.py` `GET /api/coding/trajectory/{run_id}` |
| Tier 3 mutation API | `src/keprix/mutation/self_coding_*.py` |
| Issue runner with trajectory | `src/keprix/coding/issue_runner.py` |

## Gaps this prompt closes

1. **Job page shows log lines only** - no per-step diff viewer or trajectory stepper
2. **Builder job API does not expose `trajectory[]`** - frontend cannot render patch steps
3. **Tier 3 approval not surfaced on job page** when patch is out of scope

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Step 1: Extend job detail API

Add `trajectory: PatchStep[]` to builder job detail by reading linked `trajectory_run_id` JSONL (map event types to steps).

## Step 2: Trajectory UI

Enhance `builder/jobs/[id]/page.tsx`:

- Vertical stepper per patch step
- Diff panel (reuse `CodeBlock` or diff viewer)
- Link to Tier 3 mutation card when approval required

## Step 3: Playbook node (optional thin)

`self_coding_job` node -> `startBuilderJob`; store `builder_job_id` in state. Skip if builder API lacks stable start endpoint.

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | Job with trajectory JSONL shows multi-step UI |
| 2 | Each step shows diff when present in JSONL |
| 3 | Out-of-scope patch links to mutation approve flow |
| 4 | `pytest tests/coding/test_trajectory.py` still passes |

## Archive

When AC pass.
