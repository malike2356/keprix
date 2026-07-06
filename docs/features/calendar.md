# Calendar

The workspace calendar stores events per user and supports month, week, day, and schedule views.

## Web UI (`/calendar`)

| View | Purpose |
| --- | --- |
| Month | 7-column grid; click a day to open day view |
| Week | Time grid 6 AM to 10 PM across seven days |
| Day | Single-day timeline with all-day banner |
| Schedule | Agenda list grouped by date (next 30 days) |

Toolbar: **Today**, previous/next navigation, **New event** dialog.

Click an event to view title, time range, location, and description.

## Create events

In the UI: **New event** with title, start, and end datetime.

API:

```bash
curl -X POST http://localhost:3333/api/workspace/calendar/events \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Standup",
    "start_at": "2026-07-06T09:00:00Z",
    "end_at": "2026-07-06T09:30:00Z",
    "all_day": false
  }'
```

## List events

```bash
curl "http://localhost:3333/api/workspace/calendar/events?start=2026-07-01T00:00:00Z&end=2026-07-31T23:59:59Z"
```

## CalDAV sync

Optional CalDAV sources sync external calendars:

- `GET /api/workspace/calendar/sources`
- `POST /api/workspace/calendar/sources`
- `POST /api/workspace/calendar/sync`

Configure sources when integrating Google Calendar, Nextcloud, or similar CalDAV servers.

## Agent use

ECHO persona and scheduling tools read workspace calendar availability for booking flows.

## Storage

Events live in the workspace repository (PostgreSQL in production). Back up before major upgrades.

## Related

- [Tasks](tasks.md)
- [Workspace overview](workspace.md)
