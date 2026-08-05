# Cron jobs

Cron jobs schedule recurring agent tasks with run history and failure alerts.

## Web UI (`/admin/cron`)

- List scheduled jobs with cron expressions
- Create, pause, resume, and delete jobs
- View last run status and logs

Also linked from **Settings** hub and launcher card **Cron Jobs**.

## What runs

Each job invokes an agent task or playbook on a schedule (for example daily digest, inbox triage, backup verification). Exact payload depends on job type configured in the UI.

## API

Routes under `/api/cron/*` (see [API reference](../reference/api.md)).

## Operations tips

- Use UTC or align with instance timezone in **Dashboard > Settings > General**
- Keep job prompts idempotent; retries may duplicate side effects
- Monitor failures via admin notifications

## Related

- [Trigger builder](trigger-builder.md) (preferred for new schedule/event automations)
- [Playbooks](playbooks.md)
- [Admin dashboard](../operations/admin-dashboard.md)
- [Notifications](notifications.md)
