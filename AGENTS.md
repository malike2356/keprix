# Keprix agent guidelines

Follow `/opt/lampp/htdocs/verlox/AGENTS.md` for writing style and shared Verlox rules.

## Stripe Billing Source Of Truth

Always choose Stripe price IDs and amounts from `/opt/lampp/htdocs/verlox/.stripe-credentials-and-price-id.md`. Do not create new Stripe products or prices via API, Dashboard automation, tests, or scripts unless the owner explicitly asks. Pin existing `price_*` IDs in `config/billing.yaml` (`stripe_price_id`), or via the admin pricing GUI on `/settings/billing` (`GET/PUT /api/billing/admin/pricing`). Never commit that credentials file or paste secrets into chat, logs, commits, docs, or UI.

Optional community support: open-amount "Buy me a coffee" donation (min £1, max £500). Checkout uses Stripe `price_data` via `POST /api/billing/donation/checkout` with `{ amount_gbp }`. Catalog pin `price_1Tri9T2WMXleLh8eA6gCXHbk` is documentary only for the £1 default. Not compulsory; footer sheet only; never gate Community Edition on it.

## Navigation and feature flags

- Admins/owners: full curated nav (`ui_contract/navigation.py`). Flags and simplified mode do not strip admin items.
- Users/operators: no Admin group; optional surfaces via `FLAG_NAV_GATES` / feature flags.
- Flags are progressive UX, not a full module map. Wider catalog: `/settings/modules`, `/developer/module-inventory`.

## Self-knowledge RAG

Teach Keprix about itself via the shared RAG corpus (user `__keprix_self__`):

- Index: `keprix memory index-self` or `POST /api/rag/self-knowledge/index`
- Search: `keprix memory search-self "what can you do?"` or `POST /api/rag/self-knowledge/search`
- Bootstrap on API startup when `KEPRIX_SELF_KNOWLEDGE_BOOTSTRAP=true` (default)
- Web chat injects retrieved chunks on top of `codebase_context` product brief

Do not invent a parallel vector stack; extend `memory/rag/self_knowledge.py` and `codebase_indexer.py`.
