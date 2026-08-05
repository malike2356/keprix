# Connections Tier Matrix

The connections tier matrix tracks the seven tier-1 operating domains used by Agent OS maturity scoring.

Domains: revenue, customer, calendar, comms, tasks, meetings, knowledge.

## Files

- `connections.md`: human-editable matrix.
- `connections.json`: machine-readable mirror written by Keprix.

## API

- `GET /api/agent-os/connections`
- `PUT /api/agent-os/connections`
- `POST /api/agent-os/connections/init-template`
- `POST /api/agent-os/connections/suggest-priority`

Marking a domain `live` records `connections.domain_live` for the Agent OS onboarding checklist.
