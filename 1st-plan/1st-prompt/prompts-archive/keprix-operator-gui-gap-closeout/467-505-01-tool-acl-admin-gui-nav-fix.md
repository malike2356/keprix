# Prompt 468 / 01: Tool ACL admin GUI + nav fix (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

**Depends on:** 467
**Blocks:** 505

## What was built

- Page `/admin/tool-acl` with Products, Resource grants, Check playground, Audit tabs
- Client `frontend/src/lib/tool-acl-api.ts` wired to `/api/security/acl/*`
- Nav fix: `admin-tool-acl` -> `/admin/tool-acl` in `navigation.py` + `navigation.ts`
- Admin role gate (honest message for non-admin); confirm dialogs for revoke/broad
- Docs: `docs/features/tool-acl.md`; corrected `resource-tool-acl.md`; mkdocs + governance links
- Tests: `tests/frontend/test_tool_acl_admin_gui.py` (4 passed)

## Why this exists

`/api/security/acl/*` is fully implemented (`tool_acl_routes.py`) but the
frontend had zero clients. Nav id `admin-tool-acl` label "Tool ACL" pointed at
`/admin/tools`, which is mutation-generated tools.

## Goal

Ship a real Tool ACL console and fix the nav lie.

## Acceptance

- [x] Admin can list grants and create/revoke from GUI
- [x] Check playground returns same decision as API
- [x] Nav "Tool ACL" opens ACL page, not mutation tools
- [x] Non-admin blocked

## Done When

Operators never need curl for ACL day-2 ops.
