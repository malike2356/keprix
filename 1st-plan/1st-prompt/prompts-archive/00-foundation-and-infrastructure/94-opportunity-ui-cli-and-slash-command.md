# keprix - Prompt 94: Opportunity UI, CLI, and Slash Command

**Status:** Completed. Web UI at `frontend/src/app/(workspace)/opportunities/`,
`frontend/src/lib/opportunity-api.ts`, CLI `keprix opportunity` (including `artifact`),
slash `/opportunity` in `src/keprix/opportunity/slash.py`, and tests (84 opportunity-related tests pass).

## Context

Wire Opportunity Engine into keprix's user surfaces.

The experience should be consistent across web UI, CLI, TUI, and mobile. It must feel like one keprix product, not separate tools.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Backend Routes

Use the routes from Prompt 84. Add API client support for:

- Create opportunity.
- List opportunities.
- View opportunity.
- Run full pipeline.
- Run single phase.
- Read artifacts.
- Approve pending action.
- Pause.
- Archive.

## Web UI

Create:

```text
frontend/src/app/opportunities/page.tsx
frontend/src/app/opportunities/[id]/page.tsx
frontend/src/components/opportunity/OpportunityCreatePanel.tsx
frontend/src/components/opportunity/OpportunityTimeline.tsx
frontend/src/components/opportunity/OpportunityArtifactViewer.tsx
frontend/src/components/opportunity/OpportunityScoreCard.tsx
frontend/src/components/opportunity/OpportunityApprovalQueue.tsx
frontend/src/components/opportunity/OpportunityIntegrationStatus.tsx
```

UI requirements:

- First screen is the actual opportunities workspace, not a landing page.
- Use compact professional layout.
- Use tabs for Artifacts, Score, Assets, Launch, Approvals, Growth.
- Use clear status badges.
- Approval queue must show risk, preview, integration, and action.
- No decorative orbs, no marketing hero, no explanatory feature text blocks.
- Use "playbook" consistently. Do not use deprecated recipe terminology.

## CLI

Add commands:

```text
keprix opportunity new "AI automation for estate agents"
keprix opportunity run <id>
keprix opportunity phase <id> market_demand
keprix opportunity status <id>
keprix opportunity artifact <id> 05-offer-doc.md
keprix opportunity approve <id> <approval_id>
```

## Slash Command

Add slash command:

```text
/opportunity
```

Examples:

```text
/opportunity find demand for AI automation in UK estate agencies
/opportunity run market-demand for property maintenance SaaS
/opportunity build offer from this demand report
/opportunity prepare launch plan but do not publish
```

The slash command must:

- Create or reuse an opportunity workspace.
- Ask one concise clarification only if essential.
- Default to dry run for execution.
- Summarise next actions and approval requirements.

## Mobile

If mobile exists in this keprix build, add:

- Opportunity list.
- Opportunity detail.
- Approval queue.
- Artifact reader.

Do not attempt full asset editing on mobile unless existing patterns already support it.

## Acceptance Criteria

- Users can create and run Opportunity Engine from web UI and CLI.
- `/opportunity` command works from supported chat surfaces.
- Approval queue is visible before launch execution.
- UI uses the same terminology and status names as backend.
- Tests cover API client calls, route rendering, slash command parsing, and CLI command parsing.
