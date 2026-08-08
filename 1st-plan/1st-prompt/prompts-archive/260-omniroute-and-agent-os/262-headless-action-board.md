# Keprix - Prompt 262: Headless Action Board

**Series:** Agentic OS adoption **256-265**  
**Master reference:** `../prompts-archive/ref-255-agentic-os-adoption-master-reference.md`  
**Supersedes draft:** `247-headless-skill-launcher.md`  
**Depends on:** **260**, **261**  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

**Action Board** (`/agent-os`): pinned one-click actions for skills, playbooks, and Agent Apps. Headless execution with progress, result panel, schedule shortcut, keyboard shortcuts.

Chase Level 3 without vanity metrics: show run status, tokens, duration, next schedule, approval backlog count from **261**; not social stats.

**Non-goals:** Custom Jarvis dashboard builder; Obsidian plugin.

---

## 2. Already built

| Area | Location |
| --- | --- |
| Launcher | `/launcher`, `launcherCards.ts` |
| Command palette | `CommandPalette.tsx` |
| Playbook start | `StartPlaybookDialog.tsx` |
| Agent Apps run | `/agent-apps/{name}` |
| Voice | voice feature flags |

---

## 3. Headless runners

Unified `HeadlessRunService`:

```python
async def run_skill(slug, params=None) -> HeadlessRunResult: ...
async def run_playbook(id, inputs=None) -> HeadlessRunResult: ...
async def run_agent_app(name, inputs=None) -> HeadlessRunResult: ...
```

Each creates background session, streams progress events, calls **261** ledger on complete.

API:

```
POST /api/agent-os/run/skill/{slug}
POST /api/agent-os/run/playbook/{id}
POST /api/agent-os/run/agent-app/{name}
GET  /api/agent-os/run/{run_id}/status
```

---

## 4. Action board config

```json
{
  "pins": [
    { "type": "skill", "id": "daily-brief", "label": "Morning brief" },
    { "type": "playbook", "id": "inbox-triage", "label": "Inbox brief" },
    { "type": "agent_app", "id": "daily-standup", "label": "Standup" }
  ],
  "shortcuts": { "daily-brief": "Ctrl+Shift+B" }
}
```

Stored per user in `{KEPRIX_HOME}/agent-os/action-board.json`.

---

## 5. UI layout

```text
/agent-os
  Quick pins (buttons)
  Metrics row: token burn (24h), runs today, failed runs, pending approvals
  All actions grid (search, filter by type)
  Built-in links row (chat, documents, playbooks studio)
```

Components:

- `ActionPinButton.tsx` - run + progress
- `ActionResultPanel.tsx` - output, view session, run again
- `ActionScheduleDialog.tsx` - shortcut to **260** promote/cron
- `ActionBoardMetrics.tsx` - from ledger + LLM usage API

Optional: voice trigger "run morning brief" when `voice.enabled`.

---

## 6. Launcher integration

Add **Agent OS** card to launcher pointing to `/agent-os`. Do not remove existing launcher; extend.

Command palette: `Run action: ...` filters pins.

---

## 7. Files to create

```
src/keprix/agent_os/
  headless_run_service.py
  action_board_store.py
  skill_scheduler.py          # from superseded 247 draft
  shortcut_registry.py

src/keprix/api/agent_os_run_routes.py
src/keprix/api/agent_os_board_routes.py

frontend/src/app/(workspace)/agent-os/page.tsx
frontend/src/components/agent-os/...

docs/features/agent-os-action-board.md

tests/agent_os/
  test_headless_run_service.py
  test_action_board_store.py
```

---

## 8. Acceptance criteria

- Pin skill/playbook/app; click runs headless without opening chat tab.
- Progress events update UI; failure shows debug link to session.
- Schedule opens promote flow (**260**) or cron editor with skill pre-filled.
- Keyboard shortcut runs pinned action globally in web app.
- Metrics row shows real 24h token usage and ledger counts.
- Ledger hook invoked (**261**) on every headless completion.

---

## 9. Dependencies

- **263** client kit exports `action-board.json`
- **233** studio link: "Open in studio" for pinned playbooks
