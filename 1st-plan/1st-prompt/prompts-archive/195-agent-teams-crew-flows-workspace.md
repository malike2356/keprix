# Keprix - Prompt 195: Agent Teams Playbook + Trace Gaps (Prompts 52, 58)

**Status:** Completed 2026-07-06. Tests: `test_crew_execute_node`, `test_run_events`, `test_crew`, `test_reference_adoption_smoke`.

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Teams admin UI (YAML import, run, stats) | `frontend/src/app/(workspace)/admin/teams/page.tsx` |
| Teams API client | `frontend/src/lib/teams-api.ts` |
| Crew runner backend | `src/keprix/teams/` (used by adoption smoke) |
| Nav entry | `/admin/teams` in `frontend/src/lib/navigation.ts` |
| Adoption smoke crew path | `src/keprix/playbook/adoption_release.py` |

## Gaps this prompt closes

1. **No `crew_execute` playbook node** - crews run only via admin UI or smoke script, not as durable graph nodes
2. **No live crew message feed** - run output is text blob, not per-agent trace UI
3. **No `/crew` slash command** for chat operators

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Step 1: Playbook node handler

Register `crew_execute` in `src/keprix/playbook/runtime/` (or node registry used by `runner.py`):

```python
async def crew_execute_node(state: dict, *, team_id: str, objective: str) -> dict:
    ...
```

Expose `graph_id: crew-flow` in playbook start API catalog.

## Step 2: Crew message feed

`frontend/src/components/teams/CrewMessageFeed.tsx` + `GET /api/teams/{id}/runs/{run_id}/events` (add route if missing).

Wire into `/admin/teams` run panel (replace plain text result when events available).

## Step 3: Slash command

`src/keprix/slash/commands/crew.py`: `/crew <team_id> <objective>` returns run link.

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | Playbook with `crew_execute` node completes in `tests/playbook/` |
| 2 | CrewMessageFeed renders multi-agent turns when events exist |
| 3 | `/crew` slash returns runnable admin teams URL |
| 4 | Existing `tests/integration/test_reference_adoption_smoke.py` still passes |

## Archive

When AC pass.
