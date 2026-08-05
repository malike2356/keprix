# Prompt: Adopt Agent Client Approval And Token Security For Keprix

## Goal

Protect Keprix hosted and remote-control surfaces from unknown clients, stolen tokens, suspicious automation, and public API abuse.

## Source Research

Reference only:

- `/opt/lampp/htdocs/verlox/keprix/1st-plan/competitor-research/00-agents-to-adopt/myapi-open/docs/AGENT_APPROVAL_INTEGRATION.md`
- `/opt/lampp/htdocs/verlox/keprix/1st-plan/competitor-research/00-agents-to-adopt/myapi-open/src/lib/tokenSecurityMonitor.js`
- `/opt/lampp/htdocs/verlox/keprix/1st-plan/competitor-research/00-agents-to-adopt/myapi-open/src/lib/alerting.js`

Do not copy AGPL code. Reimplement the behavior.

## Required Behavior

- Unknown remote clients enter pending approval before receiving sensitive access.
- Gate API tokens, MCP clients, agent clients, mobile/desktop sessions, and remote self-coding clients where applicable.
- First request from an unapproved client receives a pending-approval response.
- Show client fingerprint, requested scope, IP context, user agent summary, and last seen time.
- Allow approve, deny, revoke, and expiry.
- Monitor token velocity, failed auth spikes, new network patterns, user agent changes, scope violations, and suspicious generated-tool execution.
- High-risk tokens can be suspended until owner approval.
- Avoid storing raw sensitive request data when a hash or summary is enough.

## Implementation Targets To Inspect

- `src`
- `web`
- `docs/features/agent-os-client-kit.md`
- `docs/features/mcp-connector-first.md`
- `docs/features/developer-platform.md`
- Auth, token, MCP, API, and audit modules.

## Implementation Steps

1. Inventory remote access surfaces and token types.
2. Define stable client fingerprinting with privacy in mind.
3. Add pending approval storage.
4. Add guards before sensitive remote actions.
5. Add approval UI and API.
6. Add anomaly monitors with suppression windows.
7. Add automatic token suspension for configured high-risk events.
8. Add audit events and owner notifications.

## Tests

- Unknown client is blocked pending approval.
- Approved client can run allowed actions.
- Revoked or expired client is blocked.
- Velocity anomaly suspends the token when enabled.
- Scope violations are audited.
- Alert suppression prevents floods.

## Done Criteria

- Hosted Keprix can expose remote agent control safely.
- Owners can see and approve real clients.
- Stolen-token behavior is detectable and stoppable.
- No AGPL code is copied.
