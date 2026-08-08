# Prompt 392 / 03: Gap audit (nav vs tools vs channels)

Status: COMPLETED 2026-08-04
Series: Keprix capability mesh  
Depends on: 390 / 01, 391 / 02  
Blocks: 399, 400, 401  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Need an honest inventory: what is UI-only, partial, or channel-ready.

## Goal

Automate a gap report from `ui_contract` nav items + capability graph + tool registry + platform toolsets.

## Must-haves

1. CLI or script: `python -m keprix.capability_mesh.audit` (or `scripts/audit-capability-mesh.py`) printing:
   - nav id
   - graph status
   - tools present?
   - in `_KEPRIX_CORE_TOOLS` / `keprix-telegram`?
2. Write report artifact under `docs/architecture/capability-mesh-gap-report.md` (generated or committed snapshot + regenerate command).
3. Classify: `wired`, `partial`, `ui_only`, `exception` (admin-only OK).
4. Tests with fixture graph + fake registry subset.

## Nice-to-haves

1. JSON output for dashboards.

## Acceptance

- [ ] Running audit against live registry produces non-empty report.
- [ ] Top gaps for pilot (vical/calendar/contacts) are explicit if still unwired.
- [ ] Admin-only surfaces can be marked exception without failing the programme.
