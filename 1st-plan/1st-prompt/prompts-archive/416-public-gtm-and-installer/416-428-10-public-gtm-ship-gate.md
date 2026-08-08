# Prompt 426 / 10: Public GTM ship gate script + CI hook

**Status: COMPLETED 2026-08-07**  
Series: Keprix public GTM + Hermes install parity  
Depends on: 419, 420, 421, 425  
Blocks: 428  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Purpose

Fail closed before calling Keprix "public GTM ready". Add
`scripts/check-public-gtm-gate.sh` and wire it into CI or document how to run it
on release.

## Gate checks (must all pass)

1. **Anonymous GitHub reachable** (HTTP 200 on repo or raw README). If owner
   has not publicized yet, gate exits non-zero with a clear message (do not
   skip silently).
2. **No forbidden public strings** in product face:
   - `/opt/lampp/htdocs/verlox` in README + `docs/getting-started/`
   - `keprixai.uk` in frontend marketing + `docs/` + README
3. **Installer scripts syntax**: `bash -n scripts/install.sh`
4. **Install docs honesty**: fail if docs prescribe bare
   `pipx install 'keprix[tui]'` unless `KEPRIX_PYPI_PUBLISHED=1`.
5. **Re-run private quality gates** (reuse, do not rewrite):
   - `bash scripts/check-private-ship-gate.sh` OR the subset:
     TUI parity, TUI surpass, agent parity, frontend `tsc`
6. **Marketing snippet**: HowItWorks / README contain `https://` clone or curl
   one-liner.
7. Optional soft check: `curl -fsS -o /dev/null -w '%{http_code}' https://keprixai.com/`
   expects 200 when origin is live (427); allow `KEPRIX_SKIP_DOMAIN_CHECK=1`
   until origin ships.

## Tasks

1. Implement `scripts/check-public-gtm-gate.sh` with readable PASS/FAIL lines.
2. Add docs pointer in `docs/operations/readiness.md` and public sign-off (428).
3. Wire into GitHub Actions if a workflow already runs ship gates; otherwise
   document manual release requirement.
4. Do not print secrets.

## Acceptance

- [x] Script exists and is executable.
- [x] Fails today while GitHub is anonymous-404 (proves fail-closed).
- [ ] Passes on a machine after publicize + doc fixes (prove in 428).

## What was built

- `scripts/check-public-gtm-gate.sh` (7 steps; soft skips for domain + private).
- Docs: Public GTM gate section in `docs/operations/readiness.md`; pointer on 428.
- CI: `public-gtm-gate` job (surface + continue-on-error until publicize).
- Release: hard-fail `public-gtm-gate` before test/docker jobs.

## Verification

```bash
bash scripts/check-public-gtm-gate.sh; echo exit:$?
# Expect non-zero until public GitHub + doc cleanup land.
```
