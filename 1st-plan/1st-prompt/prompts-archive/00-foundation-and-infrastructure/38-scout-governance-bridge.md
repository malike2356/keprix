# keprix - Prompt 38: Scout Governance Bridge

> **Status (2026-07-05):** Bridge implemented in `src/keprix/scout/` with vault-backed API keys, signed webhook, governance UI at `/settings/governance`, and `tests/scout/test_scout_bridge.py`. Requires a live Scout instance for end-to-end enrollment against production Scout API.

## Context

Read `00a-product-vision-and-agent-consolidation-map.md` (Scout section).

Labyrinth Scout is a separate Verlox product that provides governance for AI systems:
kill switches, audit trails, policy enforcement, and blockchain trust anchoring.

keprix does not bundle Scout. Scout is a paid external service available
at `labyrinthscout.com`. keprix users who want governance pay full Scout price.

This prompt builds two things:
1. The Scout bridge: the code that connects keprix to a Scout instance when configured.
2. The Scout connector UI: the settings page that shows what Scout offers and links to
   product information, without nagging users who are not interested.

---

## Pricing Position

| Product | Scout pricing |
| --- | --- |
| keprix (self-hosted, MIT) | Full price. No discount. |
| Petraclus | 50% discount for first year (Pro and Team tiers). |
| Aiva (commercial, separate product) | Free. Included with subscription. |

Do not hardcode competitor pricing in the UI. Link to `labyrinthscout.com/pricing`
instead. The table above is for developer context only.

The connector UI must say:
"Labyrinth Scout adds kill switches, audit trails, and policy enforcement to
keprix. Available at full price from labyrinthscout.com."

It must NOT say "get a discount" or "upgrade to Petraclus for Scout discount"
in the keprix UI. Keep the message clean.

---

## Scout Bridge Implementation

`backend/scout/`

```
backend/scout/
  __init__.py
  client.py          - HTTP/WebSocket client to Scout API
  enrollment.py      - enroll this keprix instance with Scout
  heartbeat.py       - signed heartbeat every 60 seconds (cron job)
  event_reporter.py  - send security events and audit log entries to Scout
  policy_receiver.py - receive and apply policies pushed by Scout operators
  kill_relay.py      - receive Scout kill directives, halt affected operations
  routes.py          - API routes for Scout configuration
  models.py          - DB models for Scout config and event queue
```

### Database

```sql
CREATE TABLE scout_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    scout_url TEXT,
    scout_api_key_vault_id UUID,
    -- reference to vault item (Prompt 08) holding the encrypted Scout API key
    instance_id TEXT,
    -- UUID generated on enrollment, identifies this keprix instance in Scout
    enrolled_at TIMESTAMPTZ,
    last_heartbeat_at TIMESTAMPTZ,
    last_heartbeat_ok BOOLEAN,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE scout_event_queue (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    -- 'audit_log', 'security_event', 'health_metric', 'tool_execution'
    payload JSONB NOT NULL,
    sent BOOLEAN NOT NULL DEFAULT FALSE,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE scout_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_type TEXT NOT NULL,
    -- 'rate_limit', 'tool_block', 'provider_restrict', 'feature_flag'
    policy_value JSONB NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    active BOOLEAN NOT NULL DEFAULT TRUE
);
```

### Heartbeat

Every 60 seconds (via cron module, Prompt 15):
1. If Scout not enabled or not enrolled: skip.
2. Build payload: instance_id, version, uptime, provider count, active agent count.
3. Sign with HMAC-SHA256 using Scout API key.
4. POST to `{scout_url}/api/v1/heartbeat`.
5. Update `last_heartbeat_at` and `last_heartbeat_ok`.

### Event Reporting

When the audit log (Prompt 02) writes an entry and Scout is enabled:
1. Insert into `scout_event_queue`.
2. A background worker flushes the queue to Scout in batches of up to 100 every 10 seconds.
3. On 3 consecutive failures: pause Scout reporting, show a warning in governance settings.

### Policy Receiver

Scout pushes policies to keprix via signed webhook:
```
POST /api/scout/webhook
```

Policy types:
- `rate_limit`: cap agent calls per minute
- `tool_block`: disable a specific tool by name
- `provider_restrict`: restrict LLM calls to named providers
- `feature_flag`: enable or disable a named feature

Validate Scout's HMAC signature before applying any policy. Store in `scout_policies`
and apply immediately. Log each policy application to the audit log.

### Kill Switch

Kill directive types:
- `stop_agent`: stop all running agent sessions gracefully
- `lock_workspace`: workspace becomes read-only
- `disable_tools`: agent can chat but cannot execute tools

Kill directives cannot be reverted from the keprix side. Only a Scout operator
can revoke them. If the user disables Scout entirely to remove the kill switch,
they must confirm: "I accept responsibility for ungoverned operation."

---

## Scout Connector UI

`frontend/src/app/(workspace)/settings/governance/`

### When Scout is NOT connected

Page at `/settings/governance`:
- Heading: "Governance and Oversight"
- Body: "Labyrinth Scout adds real-time kill switches, tamper-evident audit trails,
  and operator-defined policy enforcement to keprix."
- Three feature bullets: Kill switches / Audit trails / Policy enforcement
- Button: "Connect Scout" (opens configuration form)
- Link: "Learn more at labyrinthscout.com" (new tab)
- Subtle footer note: "Scout is a paid service. keprix works without it."

Do not:
- Surface this page as a banner on any other workspace screen.
- Imply keprix is insecure without Scout.
- Show pricing. Link to `labyrinthscout.com/pricing` for that.

### When Scout IS connected

- Green "Connected" indicator with Scout instance name.
- Last heartbeat timestamp and status.
- "Open Scout dashboard" link (opens Scout URL).
- Active policies list (read-only in keprix).
- "Disable Scout" button with confirmation dialog.

---

## API Endpoints

```
GET  /api/scout/status     - connection status and last heartbeat
POST /api/scout/connect    - save config, test, enroll
POST /api/scout/disconnect - disable Scout (confirmation required)
POST /api/scout/webhook    - inbound from Scout (policies, kill directives)
GET  /api/scout/events     - recent queued events (debug view)
```

---

## Acceptance Criteria

- With valid Scout URL and API key, enrollment succeeds and `enrolled_at` is set.
- Heartbeat fires every 60 seconds. `last_heartbeat_ok` is true after success.
- When disabled: zero calls made to any Scout endpoint.
- A `tool_block` policy disables the named tool within 10 seconds of receipt.
- A `stop_agent` kill directive stops all active agent sessions within 5 seconds.
- Scout API key is stored in vault (Prompt 08), never in `scout_config` plaintext.
- Governance settings page shows the connector panel when Scout is not connected.
- Scout connector prompts do not appear on any other page.
- No Scout pricing comparison or Petraclus mention in the keprix UI.
