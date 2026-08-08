# Prompt 572: Cold-VM curl install proof

**Status:** SUPERSEDED 2026-08-08 by prompts 600-618
**Series:** Keprix public GTM hard-ready (570-582)  
**Depends on:** 570  
**Blocks:** 574, 582  
**Writing style:** plain ASCII only.

## Purpose

Close the open soft sign-off checkbox: prove a stranger can install on a clean
Linux VM with only the public one-liner (Hermes-class path).

## Tasks

1. On a clean Ubuntu 22.04+ VM (or equivalent container with systemd optional):
   ```bash
   curl -fsSL https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh | bash
   hash -r
   keprix --version
   ```
2. Record PASS/FAIL for: PATH, `~/.keprix` layout, venv/`[tui]`, re-run upgrade.
3. Run non-interactive setup where supported (`KEPRIX_NONINTERACTIVE=1`) with a
   throwaway or mocked provider if needed; document real key requirement.
4. Capture `keprix tui --help` or equivalent smoke (no long interactive session).
5. Optional: Docker Compose path smoke from README Option B on same VM.
6. Append evidence block to `docs/architecture/public-gtm-hard-signoff.md`
   (create stub if needed) and tick cold-VM checkbox in soft sign-off risks.

## Acceptance

- [ ] Cold install transcript or checklist dated and committed (no secrets).
- [ ] Failures become installer bugs fixed in this prompt or filed as blockers.
- [ ] Soft sign-off cold-VM checkbox updated honestly.

## Verification

```bash
# On clean VM (operator):
curl -fsSL https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh | bash
keprix --version
# Re-run installer once (idempotent)
curl -fsSL https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh | bash
```

## Notes

Do not paste API keys into docs or chat. Prefer `KEPRIX_NONINTERACTIVE` + env
provider vars for automation.
