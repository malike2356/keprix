# Prompt 582: Hard GTM ship gate and sign-off

**Status:** SUPERSEDED 2026-08-08 by prompts 600-618
**Series:** Keprix public GTM hard-ready (570-582)  
**Depends on:** 570-579 Musts; 578 decision; Nice optional  
**Blocks:** none (final)  
**Writing style:** plain ASCII only.

## Purpose

Close the programme with an automated hard gate and a written verdict that does
not inflate soft Community READY into polished market ready.

## Tasks

1. Implement `scripts/check-public-gtm-hard-gate.sh` covering at least:
   - GitHub repo 200
   - raw install.sh 200
   - keprixai.com 200
   - carinaai.uk 200 (never-break)
   - GitHub Releases >= 1
   - cold-VM evidence file present (from 572)
   - gap map Hard section exists
   - desktop: either Release assets present OR deferral doc present
   - marketing does not claim PyPI if PyPI 404
   - soft gate still runnable with skip-private
2. Write `docs/architecture/public-gtm-hard-signoff.md` with:
   - Verdict READY or BLOCKED
   - Answers to owner questions 1-8 with evidence links
   - Residual risks and owners
3. Update soft sign-off to point to hard sign-off for polished GTM.
4. Archive this pending set only when Verdict READY **or** owner accepts BLOCKED
   with deferred Musts listed (do not fake READY).

## Acceptance

- [ ] Hard gate exits 0 only when Must checks pass.
- [ ] Sign-off answers bare metal, Docker, website files, Hermes install, TUI,
      desktop, public git, market ready without contradiction.
- [ ] Contabo never-break verified in gate.

## Verification

```bash
bash scripts/check-public-gtm-hard-gate.sh
KEPRIX_PUBLIC_GTM_SKIP_PRIVATE=1 bash scripts/check-public-gtm-gate.sh
curl -fsS -o /dev/null -w '%{http_code}\n' https://carinaai.uk/
```

## Post-build

Follow `carina/01-devends/prompts-library/00-library-docs/POST-BUILD-CHECKLIST.md`
patterns: mark COMPLETED, move to
`1st-plan/1st-prompt/prompts-archive/` (or Keprix archived_prompts equivalent),
update pending README index, delete empty pending dirs.
