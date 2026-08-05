# Personal OS starter pack

Prompt **264** adds the official `keprix-personal-os-starter` Hub pack.

## Included assets

- Skills:
  - `daily-brief`
  - `inbox-triage`
  - `research-to-wiki`
  - `onboard`
  - `four-cs-audit`
  - `level-up`
- Workspace templates:
  - `knowledge_pipeline`
  - `executive_assistant`
- Daily Brief Agent App stub
- `connections.md.tpl`
- `audit-seed.json`

## Install

Install from Hub or use the Hub API:

```bash
POST /api/hub/install
{"name": "keprix-personal-os-starter", "approved": true}
```

Post-install copies the skills into `{KEPRIX_HOME}/skills`, creates a `personal-os` workspace, imports the audit seed as an editable draft, installs the Daily Brief Agent App stub, and adds suggested Action Board pins.

## Audit seed

CLI import:

```bash
keprix agent-os audit import --seed packages/packs/keprix-personal-os-starter/audit-seed.json
```

The seed creates draft workflow audit tasks for daily brief, inbox triage, and research-to-wiki.

## Readiness behavior

The sample skills degrade gracefully. If email, calendar, vault, or workspace writing is unavailable, they return a readiness note instead of crashing.
