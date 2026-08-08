# Keprix Prompt 365: Quarantine baggage and harden .gitignore

## Purpose

Remove ship-blocking baggage from the Keprix product tree without destroying
history. Move local competitor clones and retired leftovers out of the ship
path; ignore them if they reappear.

## Tasks

1. Move (do not permanently delete) if present:
   - `1st-plan/competitor-research/` -> `/opt/lampp/htdocs/verlox/archive/keprix-wip-bakups/1st-plan/competitor-research/`
   - `apps-on-keprix/retired-project-compasslab/` -> archive under the same backup root
2. Update `1st-plan/MOVED-TO-BACKUP.txt` with the new archive path and date.
3. Add gitignore entries so these paths cannot be re-added accidentally:
   - `1st-plan/competitor-research/`
   - `apps-on-keprix/retired-project-compasslab/`
   - `**/node_modules/`
   - `.venv/`, `frontend/node_modules/`, `keprix-data/`, `.pytest-data/` (confirm already covered)
4. Confirm `.env`, Stripe credential files outside the repo, and `config/billing.yaml` remain ignored.
5. Do not `git add -A`. Do not commit secrets.

## Verification

```bash
test ! -e 1st-plan/competitor-research
test ! -e apps-on-keprix/retired-project-compasslab
rg -n 'competitor-research|retired-project-compasslab' .gitignore
```
