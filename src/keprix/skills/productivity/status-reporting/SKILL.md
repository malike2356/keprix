---
name: status-reporting
description: Status report generation templates for NEXUS project dashboards.
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  keprix:
    tags: [orchestrator, nexus, reporting, status, dashboard]
    related_skills: [keprix-core-orchestrator, project-tracking]
---

# Status Reporting

Generate unified project status reports from playbook-backed project state.

## Report Sections

1. **Summary**; milestone count, blocker count, overall status
2. **Milestones**; table with status, deadline, owner
3. **Active Blockers**; dependency, deadline, and explicit block flags
4. **Agent Workstreams**; per-persona status
5. **Next Actions**; pending milestones by owner

## Usage

Call `ProjectState.generate_status_report()` after updating milestones and agent status.

Escalate when blockers are detected; present the user with concrete options, not open-ended questions.
