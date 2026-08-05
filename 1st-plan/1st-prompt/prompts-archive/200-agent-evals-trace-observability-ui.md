# Keprix - Prompt 200: Eval Trace Drill-Down Gaps (Prompt 57)

**Status:** Completed 2026-07-06. Tests: `test_eval_trace_api`, `test_evals_api`, `test_harness`, `test_trajectory`, `test_reference_adoption_smoke`.

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Evals workspace page | `frontend/src/app/(workspace)/evals/page.tsx` |
| Suite runner + release gate | `evals-harness-api.ts`, gate banner on page |
| Eval harness backend | `src/keprix/evals/`, `evals/suites/` |
| Trajectory scoring | `src/keprix/evals/scorers.py` `score_trajectory` |
| Admin session trajectory | `GET /api/admin/sessions/{id}/trajectory` |
| Adoption smoke eval step | `playbook/adoption_release.py` |

## Gaps this prompt closes

1. **No trace drawer on failed eval cases** - results show pass rate only
2. **No `GET /api/evals/traces/{trace_id}`** linking eval runs to playbook/crew/browser spans
3. **No cross-link** from eval failure to playbook run or mutation record

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Step 1: Trace API

`GET /api/evals/traces/{trace_id}` returns spans + optional `linked_run_ids` (playbook, crew, builder).

Emit `trace_id` from playbook runner and crew runner if not already on events.

## Step 2: EvalCaseResultDrawer

`frontend/src/components/evals/EvalCaseResultDrawer.tsx`:

- Open from failed suite card
- Show expected vs actual
- "View trace" span table
- Deep links when `linked_run_ids` present

Wire into `/evals` results section.

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | Failed case opens drawer with trace spans |
| 2 | Trace API returns data for smoke eval trace_id |
| 3 | Link to playbook run works when linked |
| 4 | Existing eval harness tests pass |

## Archive

When AC pass.
