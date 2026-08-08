# Prompt 578: Signed desktop artifacts or explicit defer

**Status:** SUPERSEDED 2026-08-08 by prompts 600-618
**Series:** Keprix public GTM hard-ready (570-582)  
**Depends on:** 574, 577  
**Blocks:** 582  
**Writing style:** plain ASCII only.

## Purpose

Answer owner question: can people download a desktop installable for new
features? Today: **no Release assets**. Choose ship or defer; do not leave
ambiguous marketing.

## Owner choice (pick one before build)

### Option A: Ship Community desktop artifacts

1. Build signed or at least checksummed Linux AppImage and/or `.deb`, plus macOS
   and/or Windows if CI allows.
2. Attach to GitHub Release from 574 (or a follow-up release).
3. Publish SHA256SUMS; document verify steps.
4. Marketing download page links only to those assets.
5. Smoke: install on one clean OS per artifact; open app; connect to local API.

### Option B: Explicit defer (allowed for hard GTM)

1. Write `docs/architecture/desktop-gtm-deferral.md`: not market-ready; use
   curl CLI/TUI + web UI Docker; desktop is experimental source-only.
2. Marketing must not show fake Download Desktop buttons.
3. Hard gate asserts no marketing claim of desktop binaries.

## Acceptance

- [ ] Option A assets live on a Release, OR Option B deferral doc + marketing clean.
- [ ] Hard inventory updated.

## Verification

```bash
curl -sS https://api.github.com/repos/malike2356/keprix/releases/latest | python3 -c 'import sys,json; d=json.load(sys.stdin); print([a["name"] for a in d.get("assets",[])])'
# If Option B: rg marketing for AppImage|dmg|\.deb download claims should be empty or docs-only
```
