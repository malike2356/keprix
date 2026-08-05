# Keprix Prompt 183: Agent Apps - Scheduling, Webhooks, and Public API

## Purpose

Operators automate apps **without cron YAML**: schedule from app detail, webhook URLs for
external triggers, and documented API runner. Links to `/admin/cron` for power users.

Read reference **177**. Requires **180** (stable run path) and **181** (registry metadata).
Uses `src/keprix/api/cron_routes.py` from cron admin work.

---

## Dependencies

- `src/keprix/agent_apps/web_runner.py` (`run_api`, `run_scheduled`)
- `src/keprix/api/cron_routes.py`
- `frontend/src/app/(workspace)/admin/cron/page.tsx`
- Cron job model: payload field for arbitrary JSON

---

## What to build

### 1. Schedule API

```python
POST   /api/agent-apps/{name}/schedule
GET    /api/agent-apps/{name}/schedule
DELETE /api/agent-apps/{name}/schedule
```

Body (create/update):

```json
{
  "cron": "0 9 * * 1-5",
  "timezone": "Europe/London",
  "inputs": { "focus": "Weekly goals" },
  "enabled": true
}
```

Implementation:

- Create or update cron job with `job_type: agent_app_run`, payload:
  `{ "app_name": "...", "inputs": {...}, "runner": "scheduled" }`
- Store `cron_job_id` on registry row or sidecar `schedules.json`
- Delete schedule removes cron job

### 2. Cron ticker integration

Ensure scheduler invokes agent app runner when job type matches (grep cron executor in
`src/keprix/cron/` or gateway). If missing, add handler:

```python
def execute_agent_app_job(payload: dict) -> None:
    run_scheduled(app_dir, input_text=..., context={"form": payload["inputs"]})
```

### 3. Webhook tokens

```python
POST /api/agent-apps/{name}/webhook/rotate   # returns { url, token_last4, created_at }
GET  /api/agent-apps/{name}/webhook
DELETE /api/agent-apps/{name}/webhook
```

Public route (no session cookie):

```python
POST /api/public/agent-apps/hooks/{token}
```

Body: `{ "inputs": { ... } }` or legacy `{ "input": "..." }`.

- Validate token maps to app + optional IP allowlist (env)
- Rate limit: 60/hour per token (config)
- Return same shape as `POST /api/agent-apps/{name}/run` with `runner: api`

### 4. App detail UI: Automate section

On `/agent-apps/[slug]`:

**Schedule**

- Toggle "Run on schedule"
- Cron preset chips: Daily 9am, Weekdays 9am, Weekly Monday
- Advanced: cron expression field
- Timezone selector (browser default)
- Link: "Manage all schedules in Cron admin" -> `/admin/cron`

**Webhook**

- Show URL with copy button (mask token until rotate)
- Rotate / disable buttons
- Example `curl` snippet in collapsible panel

### 5. Cron admin cross-link

On `/admin/cron` job list: column **Source** showing `Agent app: daily-standup` with link.

### 6. Developer portal snippet

Add section to `frontend/src/app/(workspace)/developer/page.tsx` or SDK page:

- Link to agent app API run endpoint
- Auth: API key header pattern used elsewhere

---

## Acceptance criteria

- [ ] Schedule creates cron job; manual cron trigger runs app (or documented gateway step).
- [ ] Webhook URL runs app without UI login (token auth).
- [ ] Uninstall removes schedule and invalidates webhook (**181** hook).
- [ ] Cron admin shows agent app source.
- [ ] Tests: schedule CRUD, webhook 401 bad token, webhook 200 good token (mock run).

---

## Out of scope

- Billing gate on scheduled runs (**184**)
- Persistent run history UI (**185**)

---

## Archive

On completion: move to `prompts-archive/`.
