# Keprix agent guidelines

Follow `/opt/lampp/htdocs/verlox/AGENTS.md` for writing style and shared Verlox rules.

## CRITICAL: 3-way deploy (local → git → Contabo)

When you finish building and have deployed or verified locally, complete all three legs in the same session unless the owner says local-only:

1. **Local** - Docker Compose smoke on the workstation.
2. **Git** - commit in `keprix/` (no secrets) and `git push origin HEAD`.
3. **Server** - rsync to Contabo `/home/malike/apps/keprix` (preserve remote `.env`), then rebuild:

```bash
rsync -az --delete \
  --exclude '.git/' --exclude '.env' --exclude '.env.*' --exclude '!.env.example' \
  --exclude '.keprix/' --exclude '.keprix-data/' --exclude 'keprix-data/' \
  --exclude 'node_modules/' --exclude 'frontend/node_modules/' --exclude 'frontend/.next/' \
  --exclude '.venv/' --exclude 'venv/' --exclude '__pycache__/' \
  /opt/lampp/htdocs/verlox/keprix/ \
  malike@80.190.81.208:/home/malike/apps/keprix/

ssh malike@80.190.81.208 'cd /home/malike/apps/keprix && docker compose \
  --project-directory /home/malike/apps/keprix \
  --env-file /home/malike/apps/keprix/.env \
  -f deploy/contabo/docker-compose.app.yml up -d --build'
```

Verify `https://app.keprixai.com/`, `/api/health`, `https://keprixai.com/`, and `https://carinaai.uk/` return HTTP 200. Contabo checkout is an rsync mirror, not a git pull. Full note: `shared/workspace-governance/THREE-WAY-DEPLOY.md` and `docs/operations/keprixai-com-origin.md`.

## Clinicom Contabo note

Contabo Clinicom (`clinicomai.com`) does **not** run on Keprix yet. Live path is Carina. When Keprix is uploaded, operators flip with `clinicom-ai/deploy/contabo-temp/switch-sidecar.sh keprix` (compose profile `keprix`). Do not treat Contabo Clinicom as Keprix-backed until that switch is done. See `shared/workspace-governance/CLINICOM-CONTABO-SIDECAR.md`.

## Stripe Billing Source Of Truth

Always choose Stripe price IDs and amounts from `/opt/lampp/htdocs/verlox/.access/.stripe-credentials-and-price-id.md`. Do not create new Stripe products or prices via API, Dashboard automation, tests, or scripts unless the owner explicitly asks. Pin existing `price_*` IDs in `config/billing.yaml` (`stripe_price_id`), or via the admin pricing GUI on `/settings/billing` (`GET/PUT /api/billing/admin/pricing`). Never commit that credentials file or paste secrets into chat, logs, commits, docs, or UI.

Optional community support: open-amount "Buy me a coffee" donation (min £1, max £500). Checkout uses Stripe `price_data` via `POST /api/billing/donation/checkout` with `{ amount_gbp }`. Catalog pin `price_1Tri9T2WMXleLh8eA6gCXHbk` is documentary only for the £1 default. Not compulsory; footer sheet only; never gate Community Edition on it.

## Navigation and feature flags

- Admins/owners: full curated nav (`ui_contract/navigation.py`). Flags and simplified mode do not strip admin items.
- Users/operators: no Admin group; optional surfaces via `FLAG_NAV_GATES` / feature flags.
- Flags are progressive UX, not a full module map. Wider catalog: `/settings/modules`, `/developer/module-inventory`.
- **New menu items:** always choose the correct existing group (Workspace, Data, Research, Apps, Automations, Security, Admin) by relevance and same-type neighbors. Do not append randomly. Keep Developer last in Admin. Sync `navigation.py` and `frontend/src/lib/navigation.ts`. Rule: `.cursor/rules/keprix-sidebar-nav.mdc`.

## Self-knowledge RAG

Teach Keprix about itself via the shared RAG corpus (user `__keprix_self__`):

- Index: `keprix memory index-self` or `POST /api/rag/self-knowledge/index`
- Search: `keprix memory search-self "what can you do?"` or `POST /api/rag/self-knowledge/search`
- Bootstrap on API startup when `KEPRIX_SELF_KNOWLEDGE_BOOTSTRAP=true` (default)
- Web chat injects retrieved chunks on top of `codebase_context` product brief

Do not invent a parallel vector stack; extend `memory/rag/self_knowledge.py` and `codebase_indexer.py`.
