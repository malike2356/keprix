# Known issues

Dated operator notes. Prefer [Troubleshooting index](index.md) for how-to fixes.

## 2026-08 (0.16.x)

| Issue | Status | Notes |
| --- | --- | --- |
| MUI `component={Link}` dead clicks in workspace | **Fixed** | Frontend uses plain `component="a"` anchors; vitest guard `mui-nav-anchor-policy`. Hard-refresh if an old bundle is cached. |
| Outreach tab / channel card navigation | **Fixed** | Same anchor policy; routes under `/outreach/*` remain valid. |
| Propreneur bridge first-user actor fallback | **Fixed** in sidecar RC | Fail-closed actor required on tool callbacks. |
| Contabo Clinicom live sidecar is Carina | By design | Keprix Clinicom flip is operator-owned; do not assume Contabo Clinicom is Keprix. |

## How to add an entry

When shipping a user-visible defect, add a row here with version, status (Open / Fixed / Accepted), and a link to the troubleshooting section.
