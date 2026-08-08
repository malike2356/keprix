# Public GTM + Hermes install gap map

**Date:** 2026-08-07  
**Programme:** Keprix IDs 416-428  
**Programme README:** `/opt/lampp/htdocs/verlox/keprix/1st-plan/1st-prompt/prompts-archive/416-428-README.md`  
**Build order:** `/opt/lampp/htdocs/verlox/keprix/1st-plan/1st-prompt/prompts-archive/ref-416-keprix-public-gtm-hermes-install-build-order.md`  
**Hermes reference (external):** https://github.com/NousResearch/hermes-agent  
**Product root inventoried:** `/opt/lampp/htdocs/verlox/keprix/`
**Sign-off:** `docs/architecture/public-gtm-signoff.md` (Verdict NOT READY; prompts archived 2026-08-07)

This map is the operational source of truth for public GTM. Quarantine (417) and
git hygiene (418) are DONE; installer/docs rewrites continue from 419. Do not treat every WORKSPACE path as delete;
prefer export-ignore / archive / ignore.

## Domain and copy facts (2026-08-07)

| Fact | Value |
| --- | --- |
| Owner public domain | `keprixai.com` |
| DNS (public A via dig) | Cloudflare anycast `104.21.16.70`, `172.67.166.227` (proxied) |
| Intended origin | Contabo `80.190.81.208` behind Cloudflare orange-cloud (owner/ref) |
| `https://keprixai.com/` | HTTP **200** (Contabo marketing FE; go-live 2026-08-07) |
| Marketing FE vs API | Frontend marketing is separable from backend for marketing-only origin |
| Marketing metadata | `metadataBase` is `https://keprixai.com` (424 DONE) |
| Anonymous GitHub | HTTP **200** (publicize 2026-08-07) |

## Live install surface checks (2026-08-07)

| Check | Result |
| --- | --- |
| `https://github.com/malike2356/keprix` (anonymous) | **404** |
| `https://pypi.org/pypi/keprix/json` | **404** |
| `https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh` | **404** |
| Local `scripts/install-curl.sh` | Pipes that raw GitHub URL (dead for strangers) |
| Local `scripts/install.sh` | Hermes-parity: piped vs checkout, `~/.keprix` home, CLI-first (Docker optional); public raw URL still 404 |
| README lead | Install-first (curl Quick Install, Docker secondary); product layout only (422) |

## A. Product vs workspace inventory

Classes: PRODUCT | DOCS | TOOLING | WORKSPACE | UNCLEAR.

| Path | Class | Notes | Closes in |
| --- | --- | --- | --- |
| `/opt/lampp/htdocs/verlox/keprix/src/` | PRODUCT | Agent runtime, API, TUI, tools | keep |
| `/opt/lampp/htdocs/verlox/keprix/frontend/` | PRODUCT | Next.js workspace + `(marketing)` | 424 (domain copy) |
| `/opt/lampp/htdocs/verlox/keprix/docker/` | PRODUCT | Primary Compose stack | 420 |
| `/opt/lampp/htdocs/verlox/keprix/docs/` | DOCS | Public MkDocs source | 423, 425 |
| `/opt/lampp/htdocs/verlox/keprix/tests/` | PRODUCT | CI / contributor tests | 426 |
| `/opt/lampp/htdocs/verlox/keprix/scripts/` | TOOLING | Installers, gates, deploy helpers | 419, 426 |
| `/opt/lampp/htdocs/verlox/keprix/config/` | PRODUCT | Billing YAML and runtime config samples | keep |
| `/opt/lampp/htdocs/verlox/keprix/migrations/` | PRODUCT | Alembic | keep |
| `/opt/lampp/htdocs/verlox/keprix/domain-packs/` | PRODUCT | First-party packs (Clinicom, research-intel, ...) | keep |
| `/opt/lampp/htdocs/verlox/keprix/evals/` | PRODUCT | Eval harnesses | keep |
| `/opt/lampp/htdocs/verlox/keprix/examples/` | DOCS | Sample usage | keep |
| `/opt/lampp/htdocs/verlox/keprix/ui/` | PRODUCT | UI contracts / web stubs | keep |
| `/opt/lampp/htdocs/verlox/keprix/mobile/` | PRODUCT | Optional mobile client | keep |
| `/opt/lampp/htdocs/verlox/keprix/sdk/` | PRODUCT | SDK surface | keep |
| `/opt/lampp/htdocs/verlox/keprix/keprix_sdk/` | PRODUCT | Packaged SDK trees | keep |
| `/opt/lampp/htdocs/verlox/keprix/packages/` | PRODUCT | Workspace packages | keep |
| `/opt/lampp/htdocs/verlox/keprix/apps/` | PRODUCT | App workspace | keep |
| `/opt/lampp/htdocs/verlox/keprix/apps-on-keprix/` | PRODUCT | Marketplace / on-Keprix apps | keep |
| `/opt/lampp/htdocs/verlox/keprix/keprix-proxy/` | PRODUCT | Credential proxy product | keep |
| `/opt/lampp/htdocs/verlox/keprix/deploy/` | TOOLING | Deploy helpers | 427 (ops notes) |
| `/opt/lampp/htdocs/verlox/keprix/database/` | PRODUCT | Schema / DB helpers | keep |
| `/opt/lampp/htdocs/verlox/keprix/templates/` | PRODUCT | Templates | keep |
| `/opt/lampp/htdocs/verlox/keprix/docker-compose*.yml` (root) | TOOLING | Extra Compose overlays (ml, searxng, localization) | 420 (honest secondary docs) |
| `/opt/lampp/htdocs/verlox/keprix/fly.toml` (+ variants) | TOOLING | Fly deploy configs | keep / document |
| `/opt/lampp/htdocs/verlox/keprix/AGENTS.md` | WORKSPACE | WORKSPACE internal; DEFERRED ok for agents; not in README lead (417) | 417 |
| `/opt/lampp/htdocs/verlox/keprix/CLAUDE.md` | WORKSPACE | WORKSPACE internal; DEFERRED ok for agents; not in README lead (417) | 417 |
| `/opt/lampp/htdocs/verlox/keprix/1st-plan/` | WORKSPACE | WORKSPACE; quarantine DONE; `.gitattributes` export-ignore DONE (418); still tracked in normal clones until owner mirror/untrack | 417, 418 |
| `/opt/lampp/htdocs/verlox/keprix/keprix-data/` | WORKSPACE | WORKSPACE; gitignored; DONE | 417 |
| `/opt/lampp/htdocs/verlox/keprix/marketing/` | WORKSPACE | was UNCLEAR; now WORKSPACE stub / gitignored; DONE (417) | 417 |
| `/opt/lampp/htdocs/verlox/keprix/site/` | WORKSPACE | was UNCLEAR; MkDocs build gitignored; DONE (417) | 417 |
| `/opt/lampp/htdocs/verlox/keprix/.venv/` | WORKSPACE | WORKSPACE; already gitignored; DONE | 417 |
| Root `README.md`, `CONTRIBUTING.md`, `LICENSE`, `SECURITY.md`, `CHANGELOG.md`, `pyproject.toml`, `uv.lock`, `mkdocs.yml`, `package.json`, `pnpm-lock.yaml` | PRODUCT / DOCS / TOOLING | Ship face | 421, 422, 425 |
| `.github/` (workflows) | TOOLING | CI including mesh gate | 426 |

## B. Hermes install UX gap map

| Hermes UX | Keprix today | Status | Closes in |
| --- | --- | --- | --- |
| Public GitHub (anonymous clone) | `github.com/malike2356/keprix` anonymous **404**; hygiene prep DONE (418) | OPEN (owner publicize remains) | 418 DONE hygiene; 428 (sign-off) |
| `curl .../install.sh | bash` | `scripts/install.sh` rewritten for pipe+checkout; `install-curl.sh` thin alias; raw URL still **404** until owner publicize | DONE (script; publicize owner) | 419 |
| Clone under `~/.hermes/hermes-agent` style home | Default `~/.keprix` + code at `~/.keprix/keprix`; README documents home paths (422) | DONE | 419, 422 |
| Binary on PATH (`hermes`) | Docs honest: curl + pipx from **git**/checkout; PyPI still **404** (publish owner later) | DONE (honesty); publish OPEN | 421 |
| `hermes setup` / chat next | Post-install prints `keprix setup` / wizard next steps; getting-started first-run docs DONE | DONE (419, 423) | 419, 423 |
| Docker full stack | Quickstart Option B + marketing/docs secondary path; strangers still cannot clone until public | DONE (docs; publicize owner) | 420 |
| Install-first README | Curl Quick Install first; Docker secondary; no abs paths / `1st-plan` in README | DONE (422); getting-started refresh DONE (423) | 422, 423 |
| Public product domain | DNS proxied; origin **200**; product/marketing copy uses `keprixai.com` | DONE | 424, 427 |

## C. OPEN / PARTIAL / DONE summary (programme)

| Gap | Status | Prompt |
| --- | --- | --- |
| Workspace noise on ship face (`1st-plan/`, data, loose scripts, marketing stub) | DONE (417) | 417 |
| Public git hygiene (ignore, export-ignore, layout) | DONE (418); GitHub anonymous still OPEN until owner flips (418/428) | 418 |
| Hermes-parity curl installer + first run | DONE (script+tests+docs note; publicize still owner) | 419 |
| Docker secondary fullstack honesty | DONE | 420 |
| PyPI / pipx honesty + release path | DONE (honesty); publish still owner later | 421 |
| README + CONTRIBUTING install-first | DONE | 422 |
| Getting-started docs refresh | DONE (423) | 423 |
| Marketing + metadata `keprixai.com` | DONE | 424 |
| MkDocs / env docs consistency | DONE | 425 |
| Public GTM ship gate + CI | DONE (fail-closed until public GitHub) | 426 |
| Contabo + Cloudflare marketing origin | DONE (runbook + nginx conf + marketing compose; live deploy OPEN) | 427 |
| Public GTM sign-off | DONE (Verdict NOT READY; prompts archived 416-428) | 428 |
| Gap map itself (this file) | DONE | 416 |
| Private soft-ship / TUI parity gates | DONE | 365-370, 341-349 (do not redo) |

## D. Owner-only actions (not agent-complete)

1. Make GitHub repo publicly readable (or publish a public mirror) before claiming curl/clone UX.
2. Approve any first PyPI upload of `keprix` (421 prepares honesty; owner uploads).
3. Contabo nginx / marketing container for `keprixai.com` origin (427 notes; owner ops).

## E. How to use this map

1. **416-428** agent prompts ARCHIVED (`prompts-archive/416-428-*.md`). Sign-off Verdict remains **NOT READY** (`docs/architecture/public-gtm-signoff.md`) until owner clears GitHub + origin (or documents deferral) and the public GTM gate is green.
2. Do not claim stranger curl/clone UX until the owner flips GitHub public (or mirror).
3. Keep absolute Verlox paths out of stranger-facing README/getting-started (417/422).
4. Re-check live HTTP codes when flipping sign-off to READY.
5. Email DNS for keprixai.com can stay OPEN until a mail provider is chosen.
6. Public GTM gate: `bash scripts/check-public-gtm-gate.sh` (expect non-zero until publicize).
7. Origin runbook: `docs/operations/keprixai-com-origin.md`; nginx source `carina/02-backends/core.carinaai.uk/docker/nginx/keprixai.com.conf`.

## F. Quarantine log (417)

Date: 2026-08-07

Moves:
- `gmail-inbox-reader.py` from `1st-plan/1st-prompt/pending-prompts/` to
  `archive/keprix-wip-bakups/pending-prompts-noise/`.

Decisions:
- `marketing/`: empty stub dirs, gitignored; live UI is `frontend/src/app/(marketing)/`.
- `site/`: MkDocs build output, already gitignored.
- `keprix-data/`: gitignored local runtime data; not in README.
- `1st-plan/`: workspace-local for Verlox agents; export-ignore deferred to 418;
  active pending prompts kept.
- README: removed absolute Verlox path lead; full install-first rewrite DONE in 422.
- `.gitignore`: ensured `*.local.md` local scratch rule.

## G. Public git hygiene log (418)

Date: 2026-08-07

- Hardened `.gitignore` secrets (`.env.*`, credentials patterns, `docker/.graphiti.env`).
- Added `.gitattributes` with `export-ignore` for `1st-plan/`, `AGENTS.md`, `CLAUDE.md`
  (affects `git archive` / some release tarballs; does not remove paths from a normal clone).
- Added `deploy/README.md` pointers and `docs/operations/public-github-checklist.md`.
- Did not untrack `1st-plan/` from the index (owner may choose a public mirror later).

## H. Curl installer log (419)

Date: 2026-08-07

- Rewrote `scripts/install.sh` for piped vs checkout detection, `KEPRIX_HOME`
  default `~/.keprix`, clone under `$KEPRIX_HOME/keprix`, uv/venv `[tui]` install,
  `~/.local/bin/keprix` symlink, optional Docker only, DRY_RUN / NONINTERACTIVE.
- `scripts/install-curl.sh` remains a thin raw-URL pipe (404 until public).
- `src/keprix/installer/paths.py`: `get_keprix_home()`; `get_install_root()`
  defaults to `~/.keprix`.
- Tests: `tests/installer/test_install_sh_hermes_layout.py`.
- README + `docs/getting-started/install.md` curl section with public-repo caveat.

## I. Docker secondary path log (420)

Date: 2026-08-07

- Rewrote `docs/getting-started/quickstart.md`: Option A curl CLI/TUI, Option B Compose full stack.
- Documented `depends_on` health order; linked VPS deploy and Compose reference.
- Marketing HowItWorks + docs `INSTALL_CMD`: curl primary, Compose full-stack secondary.
- README Option A/B pointer; `.env.example` LLM minimum comment; Compose Startup order note.
- No absolute Verlox paths in quickstart; clone URL uses `https://`.

## J. PyPI / pipx honesty log (421)

Date: 2026-08-07

- Rewrote `docs/getting-started/install.md`: curl primary; pipx from GitHub git URL;
  local checkout; no bare PyPI pipx.
- Fixed `docs/features/tui.md` voice and optional-deps install lines to git/checkout.
- Added `docs/operations/pypi-publish-checklist.md` (owner upload only).
- Extended `pyproject.toml` keywords, classifiers, and `[project.urls]`.
- Added `scripts/check-pypi-docs-honesty.sh` (skips when `KEPRIX_PYPI_PUBLISHED=1`).
- Did **not** upload to PyPI; publish remains owner-only.

## K. README install-first log (422)

Date: 2026-08-07

- Rewrote root `README.md` Hermes-style: Quick Install curl one-liner first,
  Docker full stack secondary, product-only layout, docs/CONTRIBUTING/Licence.
- Trimmed `CONTRIBUTING.md` for strangers (fork/clone, install.sh, pnpm, tests,
  Conventional Commits); depth in `docs/community/contributing.md`.
- Related products: link to `docs/community/related-projects.md` only.
- Marketing HowItWorks already had matching curl/Compose (420); no change.
- No `/opt/lampp/htdocs` or `1st-plan` in README.

## K. Getting-started docs refresh log (423)

Date: 2026-08-07

- Funnel: install.md -> first-run.md -> quickstart.md -> manual-install.md -> cloud-deploy.md.
- `install.md`: Uninstall / reset; Next links; contributor section labeled secondary.
- Rewrote `first-run.md` for CLI/TUI and Docker UI (LLM key, `keprix setup`, open product, optional messaging).
- `quickstart.md`: top links to install/first-run; Contabo marketing-origin note without programme-prompt wording.
- `manual-install.md`: titled for developers; pipx honesty; pnpm; optional install-baremetal.sh.
- `cloud-deploy.md`: Contabo vs Caddy note; curl installer vs VPS deploy scripts clarification.
- `mkdocs.yml` Getting started nav reordered to match the funnel.

