# keprix - Scout governance onboarding copy

> **Status:** Pending implementation  
> **Depends on:** Prompt 38 (`/settings/governance`, `tests/frontend/test_prompt38_guards.py`)

## Context

Operators connecting Labyrinth Scout to keprix need a clear path from purchase to paste-key-connect. Today the governance page says Scout is paid and links out, but does not explain where the API key comes from or what keprix does not automate yet.

Scout is a separate Verlox product. keprix does not sell or provision Scout. One Scout API key governs the whole keprix deployment, not individual agents.

## Goal

Add onboarding guidance on `/settings/governance` so operators understand:

1. How to obtain a Scout API key before connecting
2. That connection is manual (paste URL + key)
3. What is intentionally not built in keprix yet

## UI changes

File: `frontend/src/app/(workspace)/settings/governance/page.tsx`

### When Scout is NOT connected

Add an `Alert severity="info"` panel titled **How to connect Scout** with numbered steps:

1. Purchase Scout at [labyrinthscout.com/pricing](https://labyrinthscout.com/pricing), or use Scout included with Aiva or Carina Builder/Scale.
2. After provisioning, check your email for the Scout console URL and API key.
3. Open the Scout console and copy the API key for this deployment.
4. Click **Connect Scout** below and paste the Scout URL and API key.

Add a short note under the steps:

> One API key governs this entire keprix deployment. Individual agents do not get separate Scout keys.

Add a secondary `Alert severity="warning"` or muted callout titled **Not available in keprix yet** with bullets:

- No OAuth or "Sign in with Scout"
- No automatic key fetch after purchase
- No in-app Scout signup or billing
- No per-agent Scout keys

Keep existing feature list, Connect Scout button, external links, and footer note ("Scout is a paid service. keprix works without it.").

### Connect Scout dialog

Add helper copy above the fields:

- Scout URL: default API endpoint (`https://api.labyrinthscout.com`) unless your provisioning email says otherwise.
- Scout API key: paste the key from the Scout console or provisioning email. keprix stores it in the vault; it is never saved in plain text config.

Do not add pricing amounts. Do not mention Petraclus or discounts.

## Acceptance criteria

- Governance page shows onboarding steps when Scout is not connected.
- Copy includes "Get your API key from the Scout console after purchase" (or equivalent clear wording).
- Copy states one key per keprix deployment.
- "Not available in keprix yet" lists all four limitations.
- Connect dialog includes field-level helper text.
- No new global banners; changes stay on `/settings/governance` only.
- `tests/frontend/test_prompt38_guards.py` updated with new required copy guards.

## Test plan

```bash
cd frontend && npm run tsc -- --noEmit
PYTHONPATH=src .venv/bin/python -m pytest tests/frontend/test_prompt38_guards.py -q
```

Manual: open `/settings/governance` disconnected; confirm onboarding alert, limitations callout, and connect dialog helper text.
