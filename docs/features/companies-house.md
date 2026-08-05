# Companies House Public Data API

Live UK company search and profiles for Keprix workspaces and agents.

## Capabilities

- Search companies by name or number (`GET /api/companies-house/search`)
- Open company profile with officer summary (`GET /api/companies-house/company/{number}`)
- Agent tools: `search:companies_house`, `get:company_profile`
- Workspace UI: `/companies-house` (Research nav group)
- Settings / rotate key: `/settings/companies-house` (also on the search page)

Upstream docs: [Companies House Developer Hub](https://developer.company-information.service.gov.uk/)

## Auth

Companies House uses HTTP Basic auth: API key as username, blank password.

1. Register at the Developer Hub and create an API key application.
2. Save the key via Settings > Companies House, or set:

```bash
COMPANIES_HOUSE_API_KEY=your_key_here
KEPRIX_COMPANIES_HOUSE_ENABLED=1
```

Shared workspace note (no pasting secrets into chat): `/opt/lampp/htdocs/verlox/.access/.companies-house-api-key.md`

## Agent / Telegram / Web UI access

Companies House is part of the keprix core tool list and the configurable `companies_house` toolset. That means it is available wherever those platforms use the default core toolset, including:

| Surface | Access |
| --- | --- |
| Web UI chat | Enabled via CLI-equivalent platform toolsets |
| Telegram gateway | Via `keprix-telegram` / core tools (when gateway is running and Telegram is configured) |
| Discord / WhatsApp / Slack / other messaging platforms that use `_KEPRIX_CORE_TOOLS` | Same as Telegram |
| CLI / TUI | Core tools |
| API server toolset | Explicitly listed |

Ask the agent: "Search Companies House for BBC" or "Look up company 00000006".

## What the agent can and cannot do (honest scope)

**Can (when tools are enabled and credentials/gates pass):**

- Search UK companies; open profiles with officers summary
- Read/write workspace files via `read_file` / `write_file` / `patch` (with sandbox/ACL gates)
- Run terminal commands with dangerous-command approvals
- Use memory, web search, browser, skills, cron, messaging send, etc. from the default platform toolset

**Cannot assume / not automatic:**

- The agent does **not** magically know every Keprix HTTP admin route or every Settings panel without a tool or skill
- Full unrestricted root host access is intentionally **not** granted; egress, Tool ACL, approvals, and prompt guards still apply
- Telegram only works if the gateway bot is running and allowed for your chat; messaging tools alone are not a substitute for a live Telegram adapter
- Progressive tool disclosure (`tool_search`) may hide rarely used tools until the model searches for them
- High-risk tools can still require human confirmation (mutation install, dangerous shell, Rule of Two gates where enabled)

See also: `docs/features/agent-surface-access.md`

## Egress

Outbound calls go to `api.company-information.service.gov.uk`. The client merges that host into the `keprix` product egress allowlist before requests.

## Rate limits

Companies House rate-limits public data calls (see their developer guidelines). Keprix surfaces HTTP 429 as a clear API error; avoid tight loops when polling.
