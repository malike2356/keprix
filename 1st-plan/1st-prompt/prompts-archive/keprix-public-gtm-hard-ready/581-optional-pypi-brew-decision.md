# Prompt 581: Optional PyPI / brew decision (Owner)

**Status:** SUPERSEDED 2026-08-08 by prompts 600-618
**Series:** Keprix public GTM hard-ready (570-582)  
**Depends on:** 570, owner go/no-go  
**Priority:** Owner  
**Blocks:** none unless marketing claims them  
**Writing style:** plain ASCII only.

## Purpose

PyPI project `keprix` currently **404**. Brew tap not established. Soft GTM
honestly said not published. Only execute if owner wants publish.

## If owner says ship PyPI

1. Confirm package name availability / ownership.
2. Publish from tagged release (574); document Trusted Publishing or token in
   `.access/` (never in git).
3. Update install docs Option for `pipx install keprix[tui]`.
4. Extend honesty scripts to expect presence when flag set.

## If owner says ship brew

1. Create tap formula pointing at release tarball or PyPI.
2. Document `brew install ...`.
3. Same honesty rules.

## If owner says defer

1. Keep PyPI 404 and docs "not on PyPI".
2. Mark this prompt COMPLETED as deferred with date; do not block 582.

## Acceptance

- [ ] Either published + docs updated, or explicit defer recorded in hard sign-off.

## Verification

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://pypi.org/pypi/keprix/json
bash scripts/check-pypi-docs-honesty.sh
```
