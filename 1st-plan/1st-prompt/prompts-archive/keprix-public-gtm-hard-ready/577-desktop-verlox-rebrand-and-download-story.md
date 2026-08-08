# Prompt 577: Desktop Verlox rebrand and download story

**Status:** SUPERSEDED 2026-08-08 by prompts 600-618
**Series:** Keprix public GTM hard-ready (570-582)  
**Depends on:** 570  
**Blocks:** 578, 582  
**Writing style:** plain ASCII only.

## Purpose

Desktop under `src/keprix/apps/desktop/` still carries Nous/Hermes product
identity in places. Hard GTM cannot ship "download desktop" while strangers see
another brand.

## Tasks

1. Inventory user-visible strings: app name, about dialog, window title,
   installer metadata, tray, update feed URLs.
2. Replace Nous/Hermes branding with Keprix / Verlox-approved naming.
3. Point update/check URLs at Keprix GitHub Releases (or disable until 578).
4. Document desktop support matrix (OS, arch) in `docs/getting-started/desktop.md`
   (create if missing). Be honest if desktop is experimental.
5. Do not claim feature parity with web GUI CRM modules unless true.

## Acceptance

- [ ] No user-visible Nous/Hermes product name in desktop UI strings (spot rg).
- [ ] Desktop docs exist and match reality.
- [ ] Marketing may link to desktop only if 578 ships assets or docs say "build from source".

## Verification

```bash
rg -n 'Nous|Hermes|nousresearch' src/keprix/apps/desktop -g '!**/node_modules/**' | head -50
```
