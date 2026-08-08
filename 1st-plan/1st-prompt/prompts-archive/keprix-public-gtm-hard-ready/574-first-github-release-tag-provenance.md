# Prompt 574: First GitHub Release, tag, and provenance

**Status:** SUPERSEDED 2026-08-08 by prompts 600-618
**Series:** Keprix public GTM hard-ready (570-582)  
**Depends on:** 571, 572 (preferred), 573  
**Blocks:** 578, 582  
**Writing style:** plain ASCII only.

## Purpose

Today GitHub Releases count is **0**. Hard GTM needs a versioned, linkable
install story (not only floating `main`).

## Tasks

1. Choose version (semver from `pyproject.toml` / package version). Tag `vX.Y.Z`.
2. Create GitHub Release with notes: curl install, Docker Compose, upgrade path,
   known limits (no PyPI unless 581, desktop status from 577/578).
3. Attach or link:
   - Source archive (GitHub default) after 573 hygiene if possible.
   - Install SHA256 of `scripts/install.sh` at that tag (document in release).
4. Update marketing/docs install pages to prefer tagged install URL:
   `.../vX.Y.Z/scripts/install.sh` with fallback note for `main`.
5. Add `scripts/check-github-release-exists.sh` or extend hard gate (582).
6. Do not create Stripe prices or secrets in release notes.

## Acceptance

- [ ] `api.github.com/.../releases` returns at least one non-draft release.
- [ ] Release body lists stranger install commands that match docs.
- [ ] Tag points at a commit that passes soft public GTM gate.

## Verification

```bash
curl -sS https://api.github.com/repos/malike2356/keprix/releases/latest | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tag_name"), d.get("html_url"))'
git fetch --tags
git rev-parse "vX.Y.Z"
```
