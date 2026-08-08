# Prompt 570: Hard GTM overview inventory and DoD

**Status:** SUPERSEDED 2026-08-08 by prompts 600-618
**Series:** Keprix public GTM hard-ready (570-582)  
**Depends on:** none (start here)  
**Blocks:** 571-582  
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## Purpose

Replace soft Community GTM assumptions with a hard DoD that answers the owner
questions: bare metal, Docker, website downloads, Hermes install, TUI, desktop,
public git, market ready.

## Context (do not invent otherwise)

- Soft READY: `docs/architecture/public-gtm-signoff.md` (2026-08-07).
- Soft programme archived: `1st-plan/1st-prompt/prompts-archive/416-public-gtm-and-installer/`.
- Live (2026-08-08): GitHub 200, raw install.sh 200, keprixai.com 200, PyPI 404,
  GitHub Releases 0, desktop `src/keprix/apps/desktop/` still Nous-branded.
- Contabo product app also live at `app.keprixai.com` (beyond marketing-only note
  in older soft sign-off risks). Refresh facts in inventory.

## Tasks

1. Write or refresh `docs/architecture/public-gtm-hard-inventory.md` with a table:
   channel | path | stranger command | works today? | blocker.
2. Define hard DoD checklist in that doc (Must vs Nice vs Owner-only).
3. Wire a new gate script stub plan for 582:
   `scripts/check-public-gtm-hard-gate.sh` (implement in 582; inventory lists checks).
4. Explicitly mark what marketing may claim vs must not claim.

## Acceptance

- [ ] Inventory exists with live HTTP probes documented (date stamped).
- [ ] Must/Nice/Owner rows cover questions 1-8 from series README.
- [ ] No claim that PyPI, brew, or desktop binaries exist unless proven.
- [ ] Contabo never-break called out for any origin change.

## Verification

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://github.com/malike2356/keprix
curl -sS -o /dev/null -w '%{http_code}\n' https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh
curl -sS -o /dev/null -w '%{http_code}\n' https://keprixai.com/
curl -sS -o /dev/null -w '%{http_code}\n' https://pypi.org/pypi/keprix/json
curl -sS https://api.github.com/repos/malike2356/keprix/releases | python3 -c 'import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else d)'
```
