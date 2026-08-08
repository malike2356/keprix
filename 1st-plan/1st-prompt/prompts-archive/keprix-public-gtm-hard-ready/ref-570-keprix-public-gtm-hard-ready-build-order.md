# Build order: Keprix public GTM hard-ready (570-582)

**Writing style:** plain ASCII only.

## Parallel lanes

```text
570 inventory
   |
   +-- 571 docs/gap-map --------+
   +-- 572 cold-VM proof -------+
   +-- 573 clone hygiene -------+---- 574 Release/tag
   +-- 575 marketing CTA -------+         |
   +-- 576 SPDX (Nice) ---------+         |
                                          |
   +-- 577 desktop rebrand -----+---- 578 artifacts or defer
   +-- 579 TUI honesty ---------+---- 580 TUI bridges (Nice)
   +-- 581 PyPI/brew (Owner) ---+
                                          |
                                    582 hard sign-off
```

## Sequence rules

1. Do **570** first (DoD + inventory). Do not invent download URLs.
2. **571 + 572 + 573 + 575** can run in parallel after 570.
3. **574** needs 571 wording and preferably 572 proof notes.
4. **577** before **578**. Owner must choose: ship desktop artifacts or defer.
5. **579** before marketing claims about TUI covering CRM.
6. **581** only if owner explicitly asks to publish PyPI or brew.
7. **582** last; fail closed if Musts incomplete.

## Contabo never-break

Any Contabo marketing/nginx change: verify `https://carinaai.uk/` returns 200.
See `shared/workspace-governance/CONTABO-CARINAAI-UK-NEVER-BREAK.md`.

## 3-way deploy

When a prompt ships product code or marketing FE: local smoke, commit+push
product git root, Contabo deploy per `THREE-WAY-DEPLOY.md`.
