# Agent OS overview

Agent OS is the Keprix operating loop for finding repeated work, turning it into skills, connecting workspace memory, running actions headlessly, and handing the result to another workspace or client.

Open `/agent-os/glass` for the hub (agents, memory, tasks, tokens, ship defaults). Use `/agent-os/onboarding` for Day 1 / 7 / 30 milestones and the activation checklist. Use `/agent-os/onboard` for the seven-question interview. Memory Galaxy: `/memory/galaxy`. Usage: `/usage?days=`.

## Levels

| Level | Focus | Keprix surfaces |
| --- | --- | --- |
| L1 | Skills and loops | Workflow audit, skill proposals, promotion, loop profiles |
| L2 | Memory map | Workspace templates, vault folder, wiki documents |
| L3 | Action surface | Action board pins, headless runs, recurring schedules |
| L4 | Distribution | Client kit export and simplified mode |

The checklist stores progress per user under `{KEPRIX_HOME}/users/<user>/agent-os-onboarding.json`. Product events such as audit completion, skill approval, vault configuration, pin creation, and client kit export mark matching steps complete. Education-only or future steps can still be marked manually.

## Prompt map

| Prompt | Area |
| --- | --- |
| 256 | Workflow audit wizard |
| 257 | Session-to-skill automation loop |
| 258 | Structured workspace memory |
| 259 | Universal vault provider |
| 260 | Skill-to-automation promoter |
| 261 | Run ledger and loop profiles |
| 262 | Headless Action Board |
| 263 | Client kit and simplified mode |
| 264 | Personal OS starter pack |
| 265 | Onboarding checklist |
| 270 | Agent OS full stack (Julian Goldie blueprint): vault auto-capture, Hello World, Phases 2-5 |

## Day 1

```bash
keprix agent-os hello --name You
```

## Phase 2 workflows

```bash
keprix agent-os workflow content-series --topic "Agent OS"
keprix agent-os workflow crm-import --csv-file ./leads.csv
keprix agent-os workflow memory --query "onboarding"
```

## Phase 5 polish

UI ship defaults live on `/agent-os/glass`. CLI:

```bash
keprix agent-os playbook
keprix agent-os guardrails
keprix agent-os workflow error-paste --error "ModuleNotFoundError: No module named foo"
bash scripts/deploy-keprix-production.sh --bootstrap --domain app.example.com --skip-scout
```

See [Vault auto-capture](vault-auto-capture.md), [Phase 2 workflows](agent-os-phase2-workflows.md), [Phase 3 glass](agent-os-phase3-glass.md), [Phase 4 workflows](agent-os-phase4-workflows.md), and [Phase 5 polish](agent-os-phase5-polish.md).

## References

- Chase Agentic OS transcript: `planning/competitor-research/youtube-HRw-vP0j8OM-transcript.txt`
- Nate Herk AIOS transcript metadata: `planning/competitor-research/youtube-bCljOfCH8Ms-transcript-meta.md`
- Visual authoring layer: [Visual Playbook Studio](playbooks.md) and [Agent OS Action Board](agent-os-action-board.md)
