# Agent OS improvement loop (operator)

Run-analyzer proposals from `/api/improvement` are reviewed in the workspace GUI.

## GUI

- Review Soft Wall apply / reject / defer: `/agent-os/improvements`
- Detection toggles: `/settings/agent/self-improvement` (deep-links to the review UI)
- Skill proposals remain separate at `/agent-os/skill-proposals`

Soft Wall still wins for production workspaces even when `auto_apply_improvements` is enabled.

## API

- `GET /api/improvement/proposals`
- `POST /api/improvement/proposals/approve|reject|apply|defer`
- `GET /api/improvement/metrics`
