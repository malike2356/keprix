# Keprix Prompt 315: Docs for glass / milestones / Phase 5 API routes

## Status: DONE

## Priority

Nice, low effort.

## Context

`docs/reference/api.md` lists many Agent OS routes but omits glass, milestones, token-playbook, guardrails, and error-paste. Feature docs are CLI-heavy.

## Goal

Document the shipped endpoints and UI entry points so operators and agents stop treating Phase 3-5 surfaces as CLI-only.

## Tasks

1. Add to `docs/reference/api.md`:
   - `GET /api/agent-os/glass`
   - `GET /api/agent-os/milestones`
   - `GET /api/agent-os/token-playbook`
   - `GET /api/agent-os/guardrails`
   - `POST /api/agent-os/guardrails/backup-vault`
   - `POST /api/agent-os/error-paste`
2. Cross-link feature docs: phase3 glass, phase4 workflows, phase5 polish, overview.
3. Note UI paths: `/agent-os/glass`, `/agent-os/onboarding`, `/memory/galaxy`, `/usage`.
4. Run writing-style check if bulk-editing docs (`python3 scripts/fix-writing-style.py` from verlox).

## Acceptance criteria

- [ ] api.md lists all six routes above with method + one-line purpose.
- [ ] Feature docs mention UI paths, not only CLI.
- [ ] No em/en dashes or emojis introduced.

## Dependencies

Anytime; update again after 301-303 land if paths change.

## Files likely touched

- `docs/reference/api.md`
- `docs/features/agent-os-*.md`

## Related

- Build order: `prompts-archive/ref-301-agent-os-ui-polish-build-order.md`
