# Scout lifecycle events

Keprix emits playbook lifecycle events to Scout when `LABYRINTH_ENABLED=1` and `LABYRINTH_SCOUT_WEBHOOK_URL` is configured. Webhook failures are logged and do not fail playbook publishing or runs.

## Configuration

| Variable | Purpose |
| --- | --- |
| `LABYRINTH_ENABLED` | Enables Scout lifecycle emission |
| `LABYRINTH_SCOUT_WEBHOOK_URL` | Scout ingest webhook URL |
| `LABYRINTH_SCOUT_API_KEY` | Optional bearer token for outbound events |
| `SCOUT_CALLBACK_SECRET` | Shared secret for inbound publish callbacks |

## Event types

| Event | When |
| --- | --- |
| `playbook_publish_requested` | Publish requires Scout approval |
| `playbook_published` | Playbook version is published |
| `playbook_publish_rejected` | Scout rejects a pending publish |
| `playbook_run_completed` | A playbook run reaches a terminal status |
| `playbook_drift_sample` | Reserved for future output sample hooks |

## Run completion payload

```json
{
  "playbook_id": "daily_digest",
  "run_id": "run_123",
  "version_hash": "sha256...",
  "status": "completed",
  "duration_ms": 1280,
  "cost_usd": null,
  "step_count": 3,
  "connector_ids_used": ["notion", "slack"]
}
```

## Publish callback

Scout can approve or reject a pending publish:

```http
POST /api/scout/callbacks/playbook-publish
X-Scout-Callback-Secret: ...

{
  "playbook_id": "daily_digest",
  "version_hash": "sha256...",
  "decision": "approve",
  "reason": "Reviewed"
}
```
