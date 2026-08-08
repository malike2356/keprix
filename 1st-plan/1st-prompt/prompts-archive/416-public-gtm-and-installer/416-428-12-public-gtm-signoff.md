# Prompt 428 / 12: Public GTM sign-off and launch checklist

**Status: COMPLETED 2026-08-07**  
Series: Keprix public GTM + Hermes install parity  
Depends on: 426, 427  
Blocks: none (programme close)  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Purpose

Publish an honest public GTM sign-off. Archive this programme when Done When
passes. Do not claim Hermes parity for install UX until the gate is green.

## Tasks

1. Create `docs/architecture/public-gtm-signoff.md` with:
   - Date and scope: **public GTM / Community MIT self-host launch**
   - Explicit: this is beyond private soft-ship (365-370)
   - Evidence table:
     - `bash scripts/check-public-gtm-gate.sh` (implemented in 426; fail-closed until public GitHub)
     - Anonymous GitHub + raw install URL HTTP codes
     - Cold install notes (temp HOME) or recorded operator evidence
     - TUI parity / surpass / agent parity (reused gates)
     - `https://keprixai.com/` HTTP code (OPEN until Contabo deploy; runbook
       `docs/operations/keprixai-com-origin.md` + nginx `keprixai.com.conf` done in 427)
     - `https://carinaai.uk/` still 200 if Contabo was touched
   - Remaining risks: email DNS, PyPI unpublished, legal entity gaps, Windows
     native support limits, Contabo full API stack not deployed, etc.
2. Update series README progress checkboxes.
3. Update `pending-prompts/README.md` with programme status.
4. When fully complete and validated, archive per workspace rule:
   - Mark each prompt `**Status: COMPLETED YYYY-MM-DD**` + short What was built
   - Move `keprix-public-gtm/` set to `prompts-archive/` (keep numbering)
   - Ensure `ref-416-*.md` remains the build-order pointer
   - Delete empty pending folders
5. Owner launch checklist (manual ticks in sign-off):
- [ ] Public GitHub owner checklist: `docs/operations/public-github-checklist.md` (prepared by 418).
   - [ ] GitHub repo public
   - [ ] One-liner works on a clean Linux VM
   - [ ] README/docs match reality
   - [ ] keprixai.com serves marketing (or consciously deferred)
   - [ ] SECURITY.md contact path works
   - [ ] No secrets in public tree

## Acceptance

- [x] Sign-off doc exists and is honest.
- [x] Public GTM gate is green **or** sign-off clearly says NOT READY with
      failing checks listed (do not archive as complete if not ready).
- [x] Programme archived only when complete (kept in pending; Verdict NOT READY).

## What was built

- `docs/architecture/public-gtm-signoff.md` with Verdict **NOT READY**, evidence
  table (GitHub 404, origin 520, carinaai.uk 200, PyPI 404), owner checklist,
  flip-to-READY steps.
- Series + pending README updated; programme **not** archived.

## Verification

```bash
test -s docs/architecture/public-gtm-signoff.md
bash scripts/check-public-gtm-gate.sh
curl -fsSIL -o /dev/null -w 'github %{http_code}\n' https://github.com/malike2356/keprix
curl -fsS -o /dev/null -w 'site %{http_code}\n' https://keprixai.com/ || true
```

## Archive reminder

Canonical checklist:
`carina/01-devends/prompts-library/00-library-docs/POST-BUILD-CHECKLIST.md`
(workspace rule applies to Keprix `pending-prompts/` as well).

**2026-08-07:** Programme prompts archived to `prompts-archive/416-428-*.md`.
Public launch Verdict remains NOT READY until owner gates clear
(`docs/architecture/public-gtm-signoff.md`).
