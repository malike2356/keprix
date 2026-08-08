# Web / directory discovery

Adapter: `web_directory`

Uses the configured search backend (SearxNG / `web_search`) to produce `LeadCandidate` rows with title, URL, and snippet.

## Limits

- `max_pages` / `max_results` cap search volume per job.
- Homepage fetch for email/phone is **disabled by default**.
- Fetch requires `allow_homepage_fetch` on limits **and** `approve_homepage_fetch` in job params (Soft Wall / operator approve).
- Homepage fetch is egress-allowlist gated; denied hosts return `egress_denied` (no silent bypass).

## Domain pack templates

Examples: "plumbers in Manchester", "care homes in Kent", "estate agents in {location}".
