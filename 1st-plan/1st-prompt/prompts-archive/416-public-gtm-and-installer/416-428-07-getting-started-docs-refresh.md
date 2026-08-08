# Prompt 423 / 07: Getting-started docs refresh

**Status: COMPLETED 2026-08-07**  
Series: Keprix public GTM + Hermes install parity  
Depends on: 422  
Blocks: 425  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Purpose

Make `docs/getting-started/*` a coherent funnel: install -> first run ->
quickstart Docker -> manual/dev, matching the README story.

## Tasks

1. `install.md`: curl primary, pipx-from-git alternative, PyPI only if published.
2. `first-run.md`: admin user, LLM key, optional Telegram, open UI vs TUI.
3. `quickstart.md`: already updated in 420; ensure cross-links both ways.
4. `manual-install.md`: contributor/dev only; label clearly "for developers".
5. `cloud-deploy.md` / link to `docs/operations/vps-deploy.md`: keep accurate;
   note Contabo shared-nginx pattern differs from Caddy-only VPS (see 427).
6. Fix any broken relative links in getting-started nav (`mkdocs.yml` nav check
   in 425).
7. Add a short "Uninstall / reset" section (remove `~/.keprix`, docker compose
   down -v warning).

## Acceptance

- [x] New user can follow install.md without opening 1st-plan.
- [x] Developer path is clearly marked secondary.
- [x] No false PyPI or keprixai.uk references.

## What was built

- Funnel order in docs + `mkdocs.yml` Getting started nav.
- Uninstall / reset on install.md; Next links to first-run and quickstart.
- Rewrote first-run.md for CLI/TUI and Docker UI (`keprix setup` primary).
- Quickstart Contabo/marketing-origin note; links to install and first-run.
- Manual install retitled for developers (pnpm, pipx honesty, optional baremetal script).
- Cloud deploy Contabo vs Caddy note; fixed outdated install-curl curl|bash claim.

## Verification

```bash
rg -n 'keprixai\.uk' docs/getting-started && exit 1 || exit 0
rg -n 'curl -fsSL|pipx|docker compose' docs/getting-started/install.md docs/getting-started/quickstart.md
test -s docs/getting-started/first-run.md
```
