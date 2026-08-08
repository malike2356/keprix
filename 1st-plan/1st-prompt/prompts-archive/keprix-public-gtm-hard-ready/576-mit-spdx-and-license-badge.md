# Prompt 576: MIT SPDX and license badge accuracy

**Status:** SUPERSEDED 2026-08-08 by prompts 600-618
**Series:** Keprix public GTM hard-ready (570-582)  
**Depends on:** 570  
**Priority:** Nice  
**Blocks:** 582 (soft; Nice can be deferred with note)  
**Writing style:** plain ASCII only.

## Purpose

Soft GTM risk: LICENSE may lack SPDX identifier; badges/docs must not imply
wrong license.

## Tasks

1. Confirm root `LICENSE` is MIT and add SPDX `MIT` header/identifier if missing.
2. Align README badge and `pyproject.toml` license fields.
3. Spot-check vendored / desktop third-party notices remain accurate.
4. Do not relicense without owner.

## Acceptance

- [ ] LICENSE + package metadata agree MIT.
- [ ] README license badge matches.

## Verification

```bash
head -n 20 LICENSE
rg -n 'license|MIT|SPDX' pyproject.toml README.md | head
```
