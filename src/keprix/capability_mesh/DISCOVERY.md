# Keprix capability mesh (agent discoverability)

Workspace features link through shared object IDs and agent tools.
Channel reachability means tools in `_KEPRIX_CORE_TOOLS` / `keprix-telegram`.

## Features

### Calendar (`calendar`)
- status: `wired`
- channels: web_ui, telegram, cli
- tools: calendar_list_events
- notes: List tool in core; write stays via UI/viCal bridge.
- links: references -> `vical` via `vical_booking_id`

### Chat (`chat`)
- status: `partial`
- channels: web_ui, telegram, cli
- tools: (none listed)
- notes: Agent loop is the surface; tools come from platform toolsets.

### Companies House (`companies-house`)
- status: `wired`
- channels: web_ui, telegram, cli
- tools: search:companies_house, get:company_profile
- notes: Reference Companies House path for tool exposure.
- links: enriches -> `contacts` via `company_number`; enriches -> `memory` via `company_number`

### Contacts (`contacts`)
- status: `wired`
- channels: web_ui, telegram, cli
- tools: contacts_search, contacts_get
- notes: Search/get in core; create remains API/UI.
- links: enriches -> `memory` via `contact_id`

### Cron Jobs (`cron`)
- status: `wired`
- channels: web_ui, telegram, cli
- tools: cronjob
- links: notifies -> `chat` via `channel_target`

### Research Intel Pack (`domain-pack-research-intel`)
- status: `wired`
- channels: web_ui
- tools: create_lead, list_leads
- links: uses -> `leads`

### Scheduling Ops Pack (`domain-pack-scheduling-ops`)
- status: `wired`
- channels: web_ui
- tools: vical_offer_slots, vical_create_booking, link_booking_to_lead
- links: uses -> `vical`

### Home (`home`)
- status: `ui_only`
- channels: web_ui
- tools: (none listed)

### Leads (`leads`)
- status: `wired`
- channels: web_ui, telegram, cli
- tools: create_lead, list_leads, link_booking_to_lead
- notes: Thin product layer; not a CRM.
- links: references -> `contacts` via `contact_id`

### Memory (`memory`)
- status: `wired`
- channels: web_ui, telegram, cli
- tools: memory
- notes: Core memory tool; galaxy UI remains partial surface.

### Playbooks (`playbooks`)
- status: `partial`
- channels: web_ui, telegram, cli
- tools: (none listed)
- notes: Compose mesh tools via skills/cron; designer UI partial.
- links: schedules -> `cron` via `cron_job_id`

### Vault (`vault`)
- status: `exception`
- channels: web_ui
- tools: (none listed)
- notes: Sensitive; keep opt-in / gated, not auto channel-default.

### viCal (`vical`)
- status: `wired`
- channels: web_ui, telegram, cli
- tools: vical_offer_slots, vical_create_booking, vical_list_bookings, vical_cancel_booking
- notes: Domain+UI+agent tools; Telegram pilot mesh.
- links: creates -> `calendar` via `workspace_event_id`; references -> `contacts` via `contact_id`; links -> `leads` via `vical_booking_id`; notifies -> `chat` via `guest_email`

## Pilot verbs (Telegram / chat)

- Book / slots / bookings: `vical_offer_slots`, `vical_create_booking`, `vical_list_bookings`, `vical_cancel_booking`
- Calendar: `calendar_list_events`
- Contacts: `contacts_search`, `contacts_get`
- Companies House: `search:companies_house`, `get:company_profile`

Regenerate: `PYTHONPATH=src python3 -m keprix.capability_mesh.discovery --write`
