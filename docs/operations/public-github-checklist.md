# Public GitHub checklist

**Date:** 2026-08-07  
**Status:** DONE (repo public)  
**Audience:** Owner only (making the repository public)

This checklist prepares and records the owner action of publishing Keprix on
GitHub for anonymous clone and raw install URLs. Never paste secret values into
this document.

Related:

- Gap map: [docs/architecture/public-gtm-gap-map.md](../architecture/public-gtm-gap-map.md)
- Programme: `1st-plan/1st-prompt/prompts-archive/416-428-README.md`
- Vulnerability reporting: [SECURITY.md on GitHub](https://github.com/malike2356/keprix/blob/main/SECURITY.md)
- PyPI upload (owner later): [pypi-publish-checklist.md](pypi-publish-checklist.md)
- Sign-off: [public-gtm-signoff.md](../architecture/public-gtm-signoff.md)

## Steps

1. [x] Review the tree for secrets (never paste secret values into this doc).
2. [x] Confirm `.env.example` has no live keys.
3. [x] Flip GitHub visibility to Public (`gh repo edit malike2356/keprix --visibility public`, 2026-08-07).
4. [x] Verify: `curl -fsSIL https://github.com/malike2356/keprix` expects 200.
5. [x] Verify: `curl -fsSIL https://raw.githubusercontent.com/malike2356/keprix/main/README.md` expects 200.
6. Optional: enable branch protection on `main`; enable secret scanning / push protection in GitHub settings (no secret values here).
7. Honest note: tracked `1st-plan/` still appears in a normal clone; `export-ignore` only affects `git archive` / some release tarballs. Prefer a public ship branch or mirror without `1st-plan/` for stranger-facing clones, or untrack later with owner approval.
8. [x] After publicize: Contabo marketing origin live; public GTM sign-off READY.
