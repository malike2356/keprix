# Keprix - Prompt 196: Browser Session History Gaps (Prompts 53, 63)

**Status:** Completed 2026-07-06. Tests: `test_browser_session_history`, `test_browser_action_node`, `test_web_ui_browser_stream`, `test_reference_adoption_smoke`, `test_browser_lightpanda`.

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Browser settings + session panel | `frontend/src/app/(workspace)/settings/browser/page.tsx` |
| Browser components | `BrowserSessionPanel.tsx`, `BrowserProfileSettings.tsx` |
| Browser tool | `src/keprix/tools/browser_tool.py` |
| Dry-run in adoption smoke | `playbook/adoption_release.py` |
| Nav link | `/settings/browser` labeled "Browser" |

## Gaps this prompt closes

1. **No session history API** - `GET /api/browser/sessions` does not exist
2. **No `browser_action` playbook node** in runtime registry
3. **No dedicated `/browser` page** with history/replay (settings-only today)
4. **Chat tool_call events** lack `mode: dry_run|live` badge in stream

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Step 1: Session history routes

```python
GET /api/browser/sessions
GET /api/browser/sessions/{id}/steps
```

Persist from existing browser session store (find module; do not duplicate store).

## Step 2: Playbook node

Register `browser_action` handler; wire into adoption-smoke graph template.

## Step 3: `/browser` page

`frontend/src/app/(workspace)/browser/page.tsx`: active session + history table + step replay drawer. Point nav `browser-adoption` href here; keep profiles at `/settings/browser`.

## Step 4: Stream metadata

In `web_ui_stream.py` `_tool_progress`, include `mode` from browser tool config when `name == "browser"`.

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | Session list returns recent dry_run sessions |
| 2 | Playbook `browser_action` node runs in test |
| 3 | `/browser` renders history |
| 4 | `pytest tests/tools/test_browser_lightpanda.py` passes |

## Archive

When AC pass.
