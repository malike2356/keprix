# Headless skill execution

Skills can run without opening chat through the Agent OS action board or the compatibility skills API.

Core endpoints:

- `POST /api/skills/{skill_slug}/run`
- `GET /api/skills/{skill_slug}/runs`
- `POST /api/agent-os/run/skill/{slug}`
- `GET /api/agent-os/run/{run_id}/status`

Headless runs create a background run record and a run ledger entry for audit and review. The `/agent-os` action board provides pinned quick actions, scheduled skill runs, keyboard shortcuts on pinned actions, result review, and links into the run ledger.
