# Keprix - Prompt 197: Analytics Playbook + Research Handoff Gaps (Prompt 54)

**Status:** Completed 2026-07-06. Tests: `test_analytics_nodes`, `test_session_list`, `test_analytics_handoff`, `test_analytics_workspace`, `test_file_import`.

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Full analytics workspace UI | `frontend/src/app/(workspace)/analytics/page.tsx` (upload, charts, suggestions, Jamovi) |
| Analytics API | `frontend/src/lib/analytics-api.ts`, `src/keprix/analytics/workspace_routes.py` |
| Session create in UI | `createAnalyticsSession` wired in page |
| Code interpreter backend | `src/keprix/analytics/code_interpreter.py` |
| Adoption smoke analytics step | `playbook/adoption_release.py` |

## Gaps this prompt closes

1. **No `analytics_code` playbook node** in runtime registry
2. **No research project handoff** from analysis results
3. **No recent-sessions sidebar** (session id created but not listed/reloaded by URL)

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Step 1: Playbook node

Register `analytics_code` and `analytics_ingest` handlers using existing `CodeInterpreter`.

## Step 2: Research handoff

Button on analytics page: "Send to research project" -> `POST /api/research/projects/{id}/artifacts` with chart export + summary (use `research-workspace-api.ts`).

## Step 3: Session sidebar

`GET /api/analytics/sessions` list (add if missing); sidebar on `/analytics`; deep link `?session={id}`.

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | Playbook `data-analysis` template runs ingest + code nodes |
| 2 | Handoff creates research artifact |
| 3 | Session reloads from `?session=` query |
| 4 | Existing analytics tests pass |

## Archive

When AC pass.
