# Agent OS Phase 2 workflows (Prompt 270)

Core workflows ship as marketplace Agent Apps and CLI commands.

## Commands

```bash
keprix agent-os workflow content-series --topic "Agent OS" --questions "How do I start?"
keprix agent-os workflow crm-import --csv-file ./leads.csv --target hubspot
keprix agent-os workflow memory --query "onboarding" --note "Captured context"
keprix agent-os workflow boards
```

## Apps

Install from `/agent-apps`:

- Content Series Generator
- Memory System
- CRM Import Cleaner

## Auto-skill writing

Successful Phase 2 runs create a skill proposal under Agent OS. Set:

- `KEPRIX_AUTO_SKILL_WRITE=true` (default)
- `KEPRIX_AUTO_SKILL_APPROVE=true` to package the skill immediately (default off)

## Kanban

Content series unfinished review steps land on a workflow board JSON under
`~/.keprix/agent-os/workflow-boards/` and attempt to create Kanban tasks when
the Kanban DB is available.
