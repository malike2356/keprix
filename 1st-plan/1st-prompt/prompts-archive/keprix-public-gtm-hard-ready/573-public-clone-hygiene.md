# Prompt 573: Public clone hygiene for strangers

**Status:** SUPERSEDED 2026-08-08 by prompts 600-618
**Series:** Keprix public GTM hard-ready (570-582)  
**Depends on:** 570  
**Blocks:** 574, 582  
**Writing style:** plain ASCII only.

## Purpose

Strangers cloning `github.com/malike2356/keprix` should get a product tree, not
a Verlox planning workspace. Soft GTM noted `1st-plan/` may still appear.

## Tasks

1. Inventory tracked paths that confuse strangers: `1st-plan/`, agent-only noise,
   local logs, private Contabo notes if any leaked.
2. Choose one owner-approved approach (document choice in inventory):
   - A: `.gitattributes` `export-ignore` + release archives as stranger path, OR
   - B: stop tracking `1st-plan/` on `main` (move to private planning repo), OR
   - C: `public` branch / release branch without planning trees.
3. Implement the chosen approach without deleting company archives needed by
   Verlox agents (prefer export-ignore + clean release tarball if unsure).
4. Update CONTRIBUTING and install docs: "clone for contribute" vs "release
   archive for evaluate" if paths differ.
5. Ensure `scripts/check-public-gtm-gate.sh` forbidden-string checks still pass.

## Acceptance

- [ ] Documented stranger-facing tree policy in `docs/operations/public-github-checklist.md`.
- [ ] At least one path (release zip or branch) lacks `1st-plan/` planning noise.
- [ ] Agents still find prompts under local Verlox checkout (do not brick workspace).

## Verification

```bash
git ls-files '1st-plan/**' | wc -l
# After export-ignore / release:
# download release source zip and confirm 1st-plan absent OR document remaining risk
```
