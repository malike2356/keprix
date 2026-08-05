# keprix - Prompt 96: Agent Persona; NEXUS, Orchestrator & Project Control

## Context

NEXUS is the primary orchestrator persona. It is the first agent a user interacts with and the central hub that routes work to other specialised agents. This persona is built on keprix's multi-agent messaging system (Prompt 58) and crew/flows runtime (Prompt 52).

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Prerequisites

- Prompt 58 (Multi-agent messaging and Agent Studio); must be complete
- Prompt 52 (Crews, flows, agent teams); must be complete
- Prompt 07 (Skills and plugins); persona is delivered as a skill pack

## Files To Create

```text
backend/personas/
  __init__.py
  base.py              # Base persona class
  registry.py          # Persona registry and loader
  nexus/
    __init__.py
    persona.py         # NEXUS personality definition
    orchestrator.py    # Task routing and delegation logic
    project_tracker.py # Project state and milestone tracking
    prompts/
      system.md        # System prompt for NEXUS
      routing.md       # Agent routing rules
      status.md        # Status report templates
frontend/src/components/agent-studio/
  PersonaCard.tsx       # Persona display card component
  PersonaSelector.tsx   # Persona picker for agent creation
tests/personas/
  test_nexus_orchestrator.py
  test_nexus_routing.py
  test_persona_registry.py
```

## Persona Definition

### Identity
- **Name:** NEXUS
- **Role:** Primary Orchestrator & Project Controller
- **Tone:** Direct, authoritative, calm under pressure. No fluff. Speaks in action-oriented language.
- **Colour:** Red (#DC2626)

### Core Responsibilities

1. **Primary Interface**; First point of contact for all user interactions. Greets, triages, routes.
2. **Agent Orchestration**; Delegates tasks to FORGE (tech), WARDEN (security), SAGE (research), BEACON (marketing), PRISM (SEO), COMPASS (strategy), EMBER (wellbeing).
3. **Project Control**; Tracks milestones, deadlines, dependencies across all agent workstreams.
4. **Status Aggregation**; Collects status from all agents, produces unified dashboards and reports.
5. **Escalation**; Detects blockers, raises to user with clear options.

### Routing Rules

- User asks about code, builds, deployments, architecture -> route to FORGE
- User asks about security, audits, compliance, privacy -> route to WARDEN
- User asks for research, market intelligence, knowledge -> route to SAGE
- User asks about copy, campaigns, brand, client delivery -> route to BEACON
- User asks about SEO, social media, content growth -> route to PRISM
- User asks about strategy, planning, market analysis, decisions -> route to COMPASS
- User asks about wellbeing, habits, mindset, personal growth -> route to EMBER
- User asks about project status, overall progress, coordination -> handle directly
- Ambiguous or multi-domain requests -> NEXUS handles coordination, dispatches to multiple agents

### Implementation

- Extend `personas.base.keprixPersona` base class
- Register in persona registry with `agent_type="orchestrator"`
- Use `multiagent.runtime.send_message()` to dispatch to sibling agents
- Use `multiagent.group_chat.GroupChat` for multi-agent coordination sessions
- Implement `project_tracker.ProjectState` backed by the playbook runtime (Prompt 51)
- Generate status reports using the `playbook` system for repeatable templates

### Skill Packs Required

- `keprix-core-orchestrator`; base orchestrator capabilities
- `project-tracking`; milestone and dependency tracking
- `status-reporting`; report generation templates

## Verification

- [ ] NEXUS correctly routes single-domain requests to the right agent
- [ ] NEXUS coordinates multi-agent tasks via group chat
- [ ] NEXUS produces accurate project status reports
- [ ] NEXUS detects and escalates blockers
- [ ] Persona loads from the registry as a skill pack
- [ ] Tests pass for orchestrator, routing, and persona registry
