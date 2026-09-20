# Keprix agent guidelines


## CRITICAL: Public GitHub hygiene (product files only)

Before any commit or push to GitHub, track **only files that make this product work**. Planning docs, prompt queues, competitor research, personal notes, runtime logs, secrets, and nested foreign product trees stay workstation-local (`.gitignore` + `git rm --cached`). Canonical rule: `<workspace-root>/shared/workspace-governance/PUBLIC-GITHUB-HYGIENE.md` and `<workspace-root>/.cursor/rules/public-github-hygiene.mdc`. Guard: `bash <workspace-root>/scripts/guard-public-github-hygiene.sh`.

Follow `<workspace-root>/AGENTS.md` for writing style and shared Verlox rules.

## CRITICAL: Contabo is marketing-only for Keprix (from 2026-09-20)

Live Contabo keeps **keprixai.com** (frontend image only). Backend, Postgres,
and Redis are not run on the VPS. Installers still pull from GitHub.

- Compose: `deploy/contabo/docker-compose.marketing.yml` (no `--build` on server)
- Ship images via local build + `docker save` / `scp` / `docker load` (see
  `<workspace-root>/shared/workspace-governance/CONTABO-LOCAL-IMAGE-DEPLOY.md`)
- `https://app.keprixai.com/` redirects to `https://keprixai.com/docs`

## CRITICAL: git first; Contabo deploy prefers pre-built images

Coding agents on this workstation commit and `git push origin HEAD` only (no secrets). Stay in sync first: `git fetch`, then `git diff` against `origin/<branch>` so you never work behind a push you have not pulled.

When Contabo ship is required (owner-requested): build the frontend image **locally**, transfer it, then `up -d` with `docker-compose.marketing.yml`. Do not `docker compose ... --build` on Contabo.

### Owner-device marketing ship

1. Local: `docker build -f docker/Dockerfile.frontend -t keprix-frontend:<tag> .`
2. Transfer: `docker save ... | gzip` then `scp` + `docker load` on Contabo
3. Server: `docker compose ... -f deploy/contabo/docker-compose.marketing.yml up -d`
4. Smoke: `https://keprixai.com/` and `https://carinaai.uk/` HTTP 200

Full note: `docs/operations/keprixai-com-origin.md`, `CONTABO-LOCAL-IMAGE-DEPLOY.md`.

## Public GitHub hygiene (working product only)

The public `keprix` git tree must contain only files that ship or operate the product (runtime, frontend, SDKs, docs that operators need, tests, deploy).

**Never commit or push** internal build queues, agent prompts, competitor research, or planning scratch:

- `1st-plan/` (gitignored; keep local for prompts/archives)
- `apps-on-keprix/` (gitignored; downstream product notes stay local)
- Runtime locals: `keprix-data`, `logs/` (gitignored; never publish ACL dumps)
- Other non-product scratch under `/planning/`, `/product/`, `docs/internal/` (already ignored)

If a change does not contribute to Keprix functionality, keep it workstation-local. Do not add new ignored internal trees back into git.

## Clinicom Contabo note

Contabo Clinicom (`clinicomai.com`) does **not** run on Keprix yet. Live path is Carina. When Keprix is uploaded, operators flip with `clinicom-ai/deploy/contabo-temp/switch-sidecar.sh keprix` (compose profile `keprix`). Do not treat Contabo Clinicom as Keprix-backed until that switch is done. See `shared/workspace-governance/CLINICOM-CONTABO-SIDECAR.md`.

## Stripe Billing Source Of Truth

Always choose Stripe price IDs and amounts from `<workspace-root>/.access/.stripe-credentials-and-price-id.md`. Do not create new Stripe products or prices via API, Dashboard automation, tests, or scripts unless the owner explicitly asks. Pin existing `price_*` IDs in `config/billing.yaml` (`stripe_price_id`), or via the admin pricing GUI on `/settings/billing` (`GET/PUT /api/billing/admin/pricing`). Never commit that credentials file or paste secrets into chat, logs, commits, docs, or UI.

Optional community support: open-amount "Buy me a coffee" donation (min £1, max £500). Checkout uses Stripe `price_data` via `POST /api/billing/donation/checkout` with `{ amount_gbp }`. Catalog pin `price_1Tri9T2WMXleLh8eA6gCXHbk` is documentary only for the £1 default. Not compulsory; footer sheet only; never gate Community Edition on it.

## Navigation and feature flags

- Admins/owners: full curated nav (`ui_contract/navigation.py`). Flags and simplified mode do not strip admin items.
- Users/operators: no Admin group; optional surfaces via `FLAG_NAV_GATES` / feature flags.
- Flags are progressive UX, not a full module map. Wider catalog: `/settings/modules`, `/developer/module-inventory`.
- **New menu items:** always choose the correct existing group (Workspace, Data, Research, Apps, Automations, Security, Admin) by relevance and same-type neighbors. Do not append randomly. Keep Developer last in Admin. Sync `navigation.py` and `frontend/src/lib/navigation.ts`. Rule: `.cursor/rules/keprix-sidebar-nav.mdc`.

## Capability seams

Swappable capability contracts (Definition / Provider / Consumer) for `fs`, `shell`,
`memory`, `llm`, `subagent`, and `web` live in `keprix.seams`. Soft Wall, Channel
Shield, and vault floors wrap Providers; they do not skip the seam. Product modules
(Playbooks, CRM, billing, Document Vault) stay first-class, not plugins. Architecture:
`docs/architecture/capability-seams.md`.

## Reversible plugin lifecycle

`keprix plugins enable|disable` updates config and hot-mounts / unmounts in-process
when a PluginManager is live. Unload reverses tools, prompt sections (by section
id), MCP bindings, and seam Providers via `keprix.plugin_lifecycle`. Do not delete
plugin files on disable. Architecture:
`docs/architecture/reversible-plugin-lifecycle.md`.

## Session trajectory

Append-only session event trajectories (`keprix.trajectory`) support search,
fork, and recorded-result replay for Soft Wall / mutation debugging. UI:
`/trajectory`. Docs: `docs/architecture/session-trajectory.md`.

## Capability presets

Declarative YAML packs (`coding`, `crm`, `sidecar`) in `keprix.capability_presets`
mount plugins/skills/seams via reversible lifecycle. Soft Wall cannot be disabled
by a pack. CLI: `keprix presets`. Docs: `docs/architecture/capability-presets.md`.

## Recorded-session tests

Offline trajectory snapshot tests (`keprix.trajectory.recorded`) replay checked-in
fixtures under `tests/fixtures/trajectories/` with no LLM API keys. Docs:
`docs/architecture/recorded-session-tests.md`.

## Mutation as mount

Mutation capability changes propose mount/unmount of plugins/skills (or seam
Provider swaps), require four-eyes approval, and apply only via reversible
lifecycle. Soft Wall / RLS / first-class product modules are non-mutable on this
path. Package: `keprix.mutation.mount`. Docs:
`docs/architecture/mutation-as-mount.md`.

## Self-knowledge RAG

Teach Keprix about itself via the shared RAG corpus (user `__keprix_self__`):

- Index: `keprix memory index-self` or `POST /api/rag/self-knowledge/index`
- Search: `keprix memory search-self "what can you do?"` or `POST /api/rag/self-knowledge/search`
- Bootstrap on API startup when `KEPRIX_SELF_KNOWLEDGE_BOOTSTRAP=true` (default)
- Web chat injects retrieved chunks on top of `codebase_context` product brief
- Operator troubleshooting: `docs/troubleshooting/` (UI navigation, Soft Wall/outreach, CRM, Companies House, sidecars). After adding curated docs, extend `_SELF_DOC_PATHS` in `memory/rag/self_knowledge.py` and re-index.

Do not invent a parallel vector stack; extend `memory/rag/self_knowledge.py` and `codebase_indexer.py`.
