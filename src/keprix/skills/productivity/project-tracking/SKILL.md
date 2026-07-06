---
name: project-tracking
description: Milestone and dependency tracking for NEXUS project control.
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  keprix:
    tags: [orchestrator, nexus, project, milestones, dependencies]
    related_skills: [keprix-core-orchestrator, status-reporting]
---

# Project Tracking

Track milestones, deadlines, and dependencies across agent workstreams.

## Milestone States

- `pending`: not started
- `in_progress`: active work
- `completed`: done
- `blocked`: cannot proceed

## Dependency Rules

- A milestone with incomplete dependencies stays `pending` or `blocked`.
- NEXUS promotes milestones to `in_progress` only when all dependencies are `completed`.
- Past-deadline milestones that are not `completed` are flagged as blockers.

## Playbook Integration

Serialize project state into the playbook `state.project` bag:

```json
{
  "project": {
    "workspace_id": "...",
    "project_name": "...",
    "milestones": [],
    "agent_status": {},
    "blockers": []
  }
}
```

Use `ProjectState.from_playbook_state()` and `to_playbook_state()` when reading or writing runs.
