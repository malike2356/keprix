# Troubleshooting Keprix

Use this guide when something in the web UI, CLI, or agent loop does not behave as expected. Each section lists **Symptom → Likely cause → Fix → Related routes/docs**.

For product feature detail, start from the [full product map](../features/full-product-map.md) or the in-app Docs catalog at `/docs`.

## How to escalate

1. Note the exact URL, what you clicked, and any error text or correlation ID shown in the UI or logs.
2. Check [known issues](known-issues.md) for the running version (`keprix --version` or Settings).
3. Re-run health: `curl -s http://127.0.0.1:3333/api/health` (or your public `/api/health`).
4. If chat answers about Keprix itself are wrong, re-index self-knowledge (see [Self-knowledge](self-knowledge.md)).

## Quick links

| Problem area | Guide |
| --- | --- |
| Install, Docker, first boot | [Install and startup](install-and-startup.md) |
| Login, roles, blank workspace | [Auth and roles](auth-and-roles.md) |
| Chat silent, tools denied | [Chat and tools](chat-and-tools.md) |
| Clicks / tabs do nothing | [UI navigation](ui-navigation.md) |
| Outreach, Soft Wall, campaigns | [Soft Wall and outreach](soft-wall-and-outreach.md) |
| Standalone CRM journey / observability | [Standalone lead outreach](standalone-lead-outreach.md) |
| CRM pipeline and enrichment | [Agentic CRM](agentic-crm.md) |
| Companies House empty results | [Companies House](companies-house.md) |
| Product sidecars | [Universal sidecar](../universal-sidecar/troubleshooting.md), [Propreneur sidecar](propreneur-sidecar.md) |
| Agent answers outdated about Keprix | [Self-knowledge](self-knowledge.md) |
