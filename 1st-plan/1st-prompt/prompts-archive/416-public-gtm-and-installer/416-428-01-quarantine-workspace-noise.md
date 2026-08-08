# Prompt 417 / 01: Quarantine workspace noise from ship face

**Status: COMPLETED 2026-08-07**

Series: Keprix public GTM + Hermes install parity  
Depends on: 416  
Blocks: 418  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Purpose

Separate Verlox **workspace noise** from the **product ship face** strangers
see. Prefer move-to-archive + ignore/export-ignore over destructive delete.

## Context

365 already moved competitor research and retired Compasslab into
`/opt/lampp/htdocs/verlox/archive/keprix-wip-bakups/`. Public GTM needs a
stricter face: planning queues, local runtime data, and one-off scripts must
not look like product.

## Tasks

1. Inventory and act on noise (move if present; update
   `1st-plan/MOVED-TO-BACKUP.txt` with date and destination):
   - Loose scripts under `pending-prompts/` that are not prompts (example:
     `gmail-inbox-reader.py`) -> archive or `scripts/` only if product-useful.
   - Empty or stub `marketing/sites/keprix/` if it is not the live marketing
     surface (live marketing is `frontend/(marketing)`). Document decision.
   - Confirm `keprix-data/` stays gitignored and is not advertised in README.
   - Confirm `1st-plan/` remains **workspace-local**: either stay in working
     tree with `export-ignore` (418) or document "never publish" rule. Do not
     delete active pending prompts.
2. Add or extend ignore rules so noise cannot be re-committed:
   - `keprix-data/`
   - `1st-plan/competitor-research/` (already)
   - any `*.local.md` scratch files under repo root if used
3. Strip product-facing docs that tell users to open
   `/opt/lampp/htdocs/verlox/keprix` as if that were the public path. Replace
   with generic clone paths.
4. Do not move `src/`, `frontend/`, `docker/`, `docs/`, `tests/`, or `scripts/`
   product installers.
5. Do not `git add -A`. Do not commit secrets.

## Acceptance

- [x] Gap map WORKSPACE rows updated to DONE or DEFERRED with path.
- [x] `MOVED-TO-BACKUP.txt` updated for anything newly moved.
- [x] README / quickstart no longer lead with absolute Verlox workstation paths.
- [x] Active pending prompt series remain executable in `1st-plan/`.

## Verification

```bash
test ! -e 1st-plan/1st-prompt/pending-prompts/gmail-inbox-reader.py || true
rg -n '/opt/lampp/htdocs/verlox/keprix' README.md docs/getting-started/*.md || true
# Expect zero hits in user-facing getting-started after cleanup (internal
# AGENTS.md may still mention workspace paths).
rg -n '/opt/lampp/htdocs/verlox/keprix' README.md docs/getting-started/quickstart.md docs/getting-started/install.md docs/getting-started/first-run.md
```

Last command must exit 1 (no matches) for those four files.

## What was built

- Moved loose `gmail-inbox-reader.py` to `archive/keprix-wip-bakups/pending-prompts-noise/`.
- Documented quarantine decisions in `1st-plan/MOVED-TO-BACKUP.txt`.
- Removed absolute Verlox path lead from product `README.md`.
- Ensured `.gitignore` covers `*.local.md` plus existing data/planning/marketing/site rules.
- Added local-only `marketing/README.STUB.txt` pointing at live `(marketing)` UI.
- Updated `docs/architecture/public-gtm-gap-map.md` section A/C/E and quarantine log F.
