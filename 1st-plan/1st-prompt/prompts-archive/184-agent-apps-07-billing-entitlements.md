# Keprix Prompt 184: Agent Apps - Billing, Entitlements, and Usage Metering

## Purpose

Make Agent Apps **sellable**: plan limits on install count, runs per month, marketplace access,
scheduling, and webhooks. Upgrade CTAs in UI; enforce on API with `402 Payment Required`.

Read reference **177**. Requires **182** (tier on templates), **183** (scheduled/webhook).
Follow patterns from prompt **156** (billing UI) and `require_feature` gates.

---

## Dependencies

- `src/keprix/billing/` or `feature_gates` module
- `config/billing.yaml` or control-center feature flags
- `frontend/src/app/(workspace)/settings/` billing pages
- Catalog `tier` field from **182**

---

## What to build

### 1. Feature flags and limits

Add to billing config:

```yaml
features:
  agent_apps.enabled:
    default: true
    plans: [free, pro, team, enterprise]
  agent_apps.marketplace:
    default: true
    plans: [free, pro, team, enterprise]
  agent_apps.scheduled:
    default: false
    plans: [pro, team, enterprise]
  agent_apps.webhooks:
    default: false
    plans: [team, enterprise]
  agent_apps.publish:
    default: false
    plans: [team, enterprise]

limits:
  agent_apps.max_installed:
    free: 3
    pro: 10
    team: 50
    enterprise: unlimited
  agent_apps.max_runs_per_month:
    free: 50
    pro: 500
    team: 5000
    enterprise: unlimited
  agent_apps.max_scheduled:
    pro: 5
    team: 25
```

### 2. Usage store

SQLite table or extend existing usage DB:

```sql
agent_app_runs(id, app_name, user_id, org_id, created_at, runner, billable)
```

Increment on successful `POST /{name}/run`, webhook, and scheduled execution.

`GET /api/agent-apps/usage`:

```json
{
  "runs_this_month": 12,
  "runs_limit": 500,
  "installed_count": 2,
  "installed_limit": 10,
  "plan": "pro"
}
```

### 3. Enforcement points

| Action | Gate |
| --- | --- |
| `POST /install/*` | `agent_apps.enabled`, max_installed |
| `POST /catalog/{id}/install` | template `tier` vs plan |
| `POST /{name}/run` | enabled, max_runs_per_month |
| `POST /{name}/schedule` | `agent_apps.scheduled`, max_scheduled |
| `POST /webhook/rotate` | `agent_apps.webhooks` |
| `POST /install/upload` publish bundle | `agent_apps.publish` (team+) |

Return:

```json
HTTP 402
{
  "detail": "agent_apps.max_runs_per_month",
  "message": "You have used 50 of 50 agent app runs this month.",
  "upgrade_url": "/pricing"
}
```

### 4. Frontend upgrade UX

Components:

```text
frontend/src/components/agent-apps/AgentAppUpgradeBanner.tsx
frontend/src/components/billing/FeatureGateCard.tsx  # reuse if exists
```

- Hub banner when near limit (80% runs)
- Install button on pro template opens upgrade modal on 402
- Schedule section disabled with lock icon + "Available on Pro"
- Settings -> Usage card: agent app runs meter

### 5. Pricing page copy

Update `frontend/src/app/(marketing)/pricing/page.tsx`:

- Row: **Agent Apps** with install limits, runs, scheduling per tier
- Link to docs (placeholder until **186**)

### 6. Control center

Wire `agent_apps.enabled` toggle in control-center to actually disable routes (not docs-only).

---

## Acceptance criteria

- [ ] Free plan blocked at install limit with clear message.
- [ ] Pro template install blocked on free plan.
- [ ] Run counter increments and resets monthly.
- [ ] Schedule and webhook gated by plan.
- [ ] Tests: `tests/agent_apps/test_billing_gates.py` with mocked plan.

---

## Out of scope

- Stripe checkout changes (use existing subscription flow)
- Per-app marketplace payments

---

## Archive

On completion: move to `prompts-archive/`.
