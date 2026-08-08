# Prompt 571: Stranger docs and gap-map refresh

**Status:** SUPERSEDED 2026-08-08 by prompts 600-618
**Series:** Keprix public GTM hard-ready (570-582)  
**Depends on:** 570  
**Blocks:** 574, 575, 582  
**Writing style:** plain ASCII only.

## Purpose

Remove stale "until public / 404" stranger copy. Align gap map with READY soft
sign-off and hard inventory facts so agents and strangers are not misled.

## Tasks

1. Sweep README, `docs/getting-started/*`, `scripts/install-curl.sh` comments,
   marketing docs pages for "until public", "repo not public", false 404 caveats.
2. Rewrite `docs/architecture/public-gtm-gap-map.md` to:
   - Keep historical soft GTM rows.
   - Add **Hard GTM** section matching 570 inventory (open blockers only).
3. Ensure install docs state honestly:
   - Primary: curl | bash then `keprix setup` + LLM key + `keprix tui`.
   - Secondary: Docker Compose full stack.
   - Not available: PyPI bare install, brew (unless 581 ships).
4. Run `scripts/check-pypi-docs-honesty.sh` and fix any drift.
5. Do not put `/opt/lampp/htdocs/verlox` into stranger docs.

## Acceptance

- [ ] No stranger-facing claim that GitHub is private.
- [ ] Gap map Hard section lists Releases=0, desktop Nous, cold VM unchecked, etc.
- [ ] PyPI honesty script exits 0.
- [ ] Surface public GTM gate still exits 0 with `KEPRIX_PUBLIC_GTM_SKIP_PRIVATE=1`.

## Verification

```bash
rg -n 'until public|not public|404' README.md docs/getting-started scripts/install-curl.sh || true
KEPRIX_PUBLIC_GTM_SKIP_PRIVATE=1 bash scripts/check-public-gtm-gate.sh
bash scripts/check-pypi-docs-honesty.sh
```
