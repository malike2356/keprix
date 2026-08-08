# Calendar

The workspace calendar stores events per user and supports month, week, day, and schedule views. It syncs with external calendars over CalDAV (bidirectional) or ICS feeds (pull only), with optional automatic resync on a configurable interval.

## Web UI (`/calendar`)

| View | Purpose |
| --- | --- |
| Month | 7-column grid; click a day to open day view |
| Week | Time grid 6 AM to 10 PM across seven days |
| Day | Single-day timeline with all-day banner |
| Schedule | Agenda list grouped by date (next 30 days) |

Toolbar: **Today**, previous/next navigation, **New event**, **New booking**, **Sync calendars**, **Sync now**.

Deep links:

| Query | Behaviour |
| --- | --- |
| `/calendar?event={id}` | Opens day view on that event and shows the detail dialog |
| Event with `metadata.vical_booking_id` | Detail dialog includes **Open booking** → `/vical?booking=...` |

Click an empty hour on week or day view to create a viCal booking for that free slot (host `POST /api/vical/bookings` with `skip_slot_check`).

## Automated 2-way sync

Open **Sync calendars** → **Connect calendar**.

| Setting | Default | Notes |
| --- | --- | --- |
| Sync direction | `bidirectional` (CalDAV) | ICS is always `pull` |
| Push local events | On for CalDAV | New/edited Keprix events push to the connected calendar |
| Auto-sync | On | Background worker resyncs when due |
| Resync interval | 15 minutes | Configurable per source: 5m to 24h |

The API process runs a calendar auto-sync scheduler (same lifespan pattern as email/contact sync). It ticks every ~30s and syncs each source whose `last_sync_at` is older than its interval.

Kill switch: `KEPRIX_CALENDAR_AUTO_SYNC=0`. Tick override: `KEPRIX_CALENDAR_SYNC_TICK_SEC=30`.

### Provider guidance for automation

| Provider | Mode | Continual automation |
| --- | --- | --- |
| Google CalDAV | 2-way | Preferred Google path for auto sync |
| Google ICS | Pull | OK for read-only refresh; not 2-way |
| iCloud / Nextcloud / Fastmail / CalDAV | 2-way | Preferred for write-back |
| ICS feed | Pull | Interval refresh only |

## Sync API

```bash
# Scheduler status
curl http://localhost:3334/api/workspace/calendar/auto-sync

# Connect CalDAV with auto 2-way every 15 minutes
curl -X POST http://localhost:3334/api/workspace/calendar/sources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Work",
    "provider": "nextcloud",
    "url": "https://cloud.example/remote.php/dav/",
    "username": "alice",
    "password": "...",
    "sync_direction": "bidirectional",
    "push_local_events": true,
    "auto_sync": true,
    "sync_interval_minutes": 15
  }'

# Change interval / pause auto-sync
curl -X PATCH http://localhost:3334/api/workspace/calendar/sources/{id} \
  -H "Content-Type: application/json" \
  -d '{"sync_interval_minutes": 60, "auto_sync": true}'

# Manual sync
curl -X POST http://localhost:3334/api/workspace/calendar/sync
```

## Create / list events

```bash
curl -X POST http://localhost:3334/api/workspace/calendar/events \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Standup",
    "start_at": "2026-07-06T09:00:00Z",
    "end_at": "2026-07-06T09:30:00Z"
  }'

curl "http://localhost:3334/api/workspace/calendar/events?start=2026-07-01T00:00:00Z&end=2026-07-31T23:59:59Z"
```

## Storage

Events and sources persist under the Keprix data directory (`workspace/calendar_store.json` for the in-memory repository path). Passwords/tokens are encrypted at rest.

## Related

- [Tasks](tasks.md)
- [Workspace overview](workspace.md)
