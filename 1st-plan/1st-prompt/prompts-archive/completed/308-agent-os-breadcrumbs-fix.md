# Keprix Prompt 308: Fix Agent OS breadcrumbs

## Status: DONE

## Priority

Should, low effort.

## Context

Several Agent OS pages breadcrumb "Agent OS" to `/agent-os/audit` instead of `/agent-os` or `/agent-os/glass`. That trains users into the wrong home.

## Goal

Standardize breadcrumbs so parent **Agent OS** links to the hub home (glass after 301, or `/agent-os`). Audit remains a child crumb when on audit.

## Tasks

1. Grep Agent OS pages for breadcrumb hrefs pointing at `/agent-os/audit`.
2. Replace parent link with hub home (`/agent-os/glass` preferred once 301 ships).
3. Pattern: `Agent OS / <Page>` or `Agent OS / Audit / ...` as needed.
4. Align with PageHeader breadcrumb API used elsewhere.

## Acceptance criteria

- [ ] No Agent OS page uses audit as the parent hub link.
- [ ] Parent always reaches glass or board hub in one click.
- [ ] Audit page still reachable from hub secondary links.

## Dependencies

After **301** (know which href is hub home).

## Files likely touched

- `frontend/src/app/(workspace)/agent-os/**/page.tsx`
- Shared breadcrumb helpers if any

## Related

- Build order: `reference/301-agent-os-ui-polish-build-order.md`
