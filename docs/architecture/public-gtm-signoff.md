# Public GTM sign-off

**Date:** 2026-08-07 (READY update same day after publicize + Contabo origin)  
**Scope:** public GTM / Community MIT self-host launch (Hermes-class install UX)  
**Programme:** Keprix IDs 416-428 (prompts archived)  
**Verdict:** **READY** for public Community self-host GTM (with remaining risks below)

This is beyond private soft-ship (365-370). See [private-ship-signoff.md](private-ship-signoff.md).

## Programme agent work (416-428)

Archived under `1st-plan/1st-prompt/prompts-archive/416-428-*.md`.

## Evidence (2026-08-07 go-live)

| Check | Result |
| --- | --- |
| `KEPRIX_PUBLIC_GTM_SKIP_PRIVATE=1 bash scripts/check-public-gtm-gate.sh` | **PASS** (after publicize + origin + docs cleanup) |
| `https://github.com/malike2356/keprix` (anonymous) | HTTP **200** |
| Raw README / `scripts/install.sh` | HTTP **200** |
| Cold curl install | Public raw URL reachable; operator should spot-check on a clean VM |
| TUI / agent parity | Scripts present; last full private-ship green recorded 2026-07-27; re-run private gate before a major release cut if desired |
| `https://keprixai.com/` | HTTP **200** (Contabo marketing FE + nginx vhost) |
| `https://www.keprixai.com/` | redirects to apex (200) |
| Origin runbook | `docs/operations/keprixai-com-origin.md` |
| Nginx source | `carina/02-backends/core.carinaai.uk/docker/nginx/keprixai.com.conf` |
| Contabo deploy | Marketing-only `keprix-frontend` on `proxy`; debug bind `127.0.0.1:13000` |
| `https://carinaai.uk/` | HTTP **200** after Contabo nginx changes |
| PyPI `keprix` | HTTP **404** (optional; docs stay honest; curl/git install is primary) |

## Owner launch checklist

- [x] Public GitHub checklist: `docs/operations/public-github-checklist.md`
- [x] GitHub repo public (anonymous 200)
- [ ] One-liner spot-check on a clean Linux VM (operator)
- [x] README/docs match public install story
- [x] keprixai.com serves marketing
- [x] SECURITY.md contact path on public repo
- [x] No secrets intended in public tree (keep scanning)
- [x] Surface public GTM gate exits 0 (`KEPRIX_PUBLIC_GTM_SKIP_PRIVATE=1`)

## Remaining risks (honest)

- Email DNS (MX/SPF/DKIM/DMARC) for keprixai.com not configured.
- PyPI package unpublished; bare `pipx install 'keprix[tui]'` remains forbidden until owner upload.
- Hosted SaaS legal entity / paid conversion copy still incomplete.
- Windows native support limits unchanged.
- Contabo full Keprix API stack not deployed (marketing-only origin by design for this launch).
- Tracked `1st-plan/` may still appear in a normal clone; prefer clean release tags / archive exports for strangers.
- Full private ship gate not re-run in this go-live session (surface gate green).

## Related

- Gap map: [public-gtm-gap-map.md](public-gtm-gap-map.md)
- Private soft-ship: [private-ship-signoff.md](private-ship-signoff.md)
- Readiness / gates: `docs/operations/readiness.md`
- Origin: `docs/operations/keprixai-com-origin.md`
- Archived prompts: `1st-plan/1st-prompt/prompts-archive/416-428-*.md`
