# TUI and web workspace surface matrix

**Updated:** 2026-08-08

The TUI is the core agent command centre. The web workspace remains the detailed
operator interface for visual and high-density workflows. A bridge can summarize a
module or open its web route without claiming full terminal CRUD.

| Feature area | Web route | TUI state |
| --- | --- | --- |
| Agent chat and streaming tools | `/home` | Full |
| Sessions, models, skills, plugins | Workspace routes | Full core controls |
| Setup, status, diagnostics | `/settings` and admin readiness | Full CLI and partial TUI |
| Approvals and Soft Wall | `/approvals`, CRM settings | Partial; approval overlays, detailed policy remains web |
| Agentic CRM pipeline | `/crm` | Partial; agent tools and summaries, visual board remains web |
| CRM enrich and discovery jobs | `/crm/enrich` | Partial; agent tools, detailed review remains web |
| CRM workflow designer and analytics | `/crm/workflows`, `/crm/analytics` | Web only visual experience |
| Spreadsheet preprocessing | `/data` | Partial through agent tools; visual mapping remains web |
| Playbook studio | `/playbooks` | Partial; execution available, visual authoring remains web |
| Sidecar project management | `/settings/sidecars` | Partial through agent tools and API; pairing GUI remains web |
| viCal bookings | `/vical` | Partial through agent tools; calendar board remains web |
| Backup, restore, upgrade | Settings and admin routes | Full CLI lifecycle; web adds guided forms |
| Billing and tenant administration | Admin routes | Web only |

Install documentation may direct users to `keprix tui` for core agent use. It must
not describe every visual CRM, analytics, billing, or administration surface as
fully reproduced in the terminal.
