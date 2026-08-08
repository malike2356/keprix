# keprix - Prompt: Mandatory Agent Routing Guide (Adopting OpenMontage's AGENT_GUIDE.md Pattern)

## Purpose

OpenMontage uses a simple but effective pattern: `AGENTS.md` contains only one instruction -- "read `AGENT_GUIDE.md` before responding to ANY message." The guide file contains routing rules that determine the agent's first action. This prevents the agent from skipping context and taking wrong actions.

keprix's NEXUS persona (the orchestrator that routes tasks to sub-agents) should adopt this pattern. Currently NEXUS loads its system prompt and immediately starts routing. With the guide pattern, NEXUS reads its routing guide first, checks which persona is best suited, and only then acts.

This is not complex to build. It's one markdown file and a system prompt instruction. The value is in the behavioural constraint: the agent cannot skip the guide.

## What to build

### 1. NEXUS Routing Guide

```
skills/personas/nexus/AGENT_GUIDE.md

# NEXUS -- Routing Guide

Read this before responding to ANY message. Do not act until you have read
and understood this guide.

## Routing Decision Tree

For every user request, determine which persona should handle it:

1. Is this about code, development, or technical implementation?
   -> FORGE (full-stack), CODEX (code-only)

2. Is this about security, compliance, vulnerabilities, or auditing?
   -> WARDEN

3. Is this about research, information gathering, or knowledge synthesis?
   -> SAGE

4. Is this about marketing, content creation, campaigns, or client delivery?
   -> BEACON (marketing), PRISM (SEO/content)

5. Is this about strategy, decisions, business planning, or prioritisation?
   -> COMPASS

6. Is this about scheduling, calendar, messages, reception, or admin?
   -> ECHO

7. Is this about wellbeing, coaching, habits, or personal development?
   -> EMBER

8. Is this a complex task spanning multiple domains?
   -> NEXUS (you) -- decompose into sub-tasks, route to appropriate personas,
      then synthesise the results.

## Routing Rules

- Route to ONE persona per sub-task. Do not send the same request to multiple personas.
- If uncertain between two personas, pick the more specific one.
  CODEX > FORGE for pure coding. PRISM > BEACON for SEO work.
- If the request spans 3+ domains, handle it yourself as NEXUS. Decompose it,
  route sub-tasks, and synthesise.
- Each persona has its own SKILL.md. Read it before routing to understand
  what that persona can and cannot do.
- If no persona fits, handle the request yourself. Do not route to a persona
  that is not suited to the task.

## Persona Capability Summary

| Persona | Best for | Avoid for |
|---------|----------|-----------|
| FORGE | Full-stack dev, architecture, deployment | Pure research, security audits |
| CODEX | Code review, refactoring, bug fixes | Architecture decisions, deployment |
| WARDEN | Security audits, hardening, compliance | General coding, marketing |
| SAGE | Research, information synthesis | Code execution, deployment |
| BEACON | Marketing campaigns, content, delivery | Security, legal advice |
| PRISM | SEO, organic growth, content strategy | General marketing strategy |
| COMPASS | Strategy, decisions, prioritisation | Hands-on implementation |
| ECHO | Scheduling, admin, reception, calendar | Complex analysis, strategy |
| EMBER | Wellbeing, coaching, habits | Business strategy, coding |

## After Routing

Once you have routed to a persona:
1. Tell the user which persona is handling their request and why.
2. Pass the full context to the persona. Include relevant workspace files,
   memory entries, and conversation history.
3. When the persona returns, verify the output before presenting it to the user.
4. If the output is incomplete or incorrect, route to the same persona with
   specific feedback, or handle it yourself.

## When NOT to Route

- Simple factual questions: answer directly. Do not route.
- Requests to explain what you (NEXUS) can do: answer directly.
- The user explicitly asks for you (NEXUS) specifically.
- The task is trivial and routing would add unnecessary overhead.
```

### 2. Mandatory Guide Instruction in System Prompt

NEXUS's system prompt gets a single instruction at the top:

```python
NEXUS_SYSTEM_PROMPT = """
**MANDATORY: Read skills/personas/nexus/AGENT_GUIDE.md before responding
to ANY user message.** Do not act on the user's request until you have
read the routing guide. It contains the decision tree that determines
your first action. Skipping it WILL cause you to route to the wrong persona.

{rest_of_nexus_prompt}
"""
```

The key: this is the FIRST line. Nothing above it. The agent cannot miss it.

### 3. Pattern Applied to Other Personas

The pattern is generalisable. Every persona can have its own AGENT_GUIDE.md with domain-specific routing:

```
skills/personas/warden/AGENT_GUIDE.md  -- security escalation paths
skills/personas/sage/AGENT_GUIDE.md    -- research depth levels
skills/personas/echo/AGENT_GUIDE.md    -- escalation triggers for calls
```

The system prompt for each persona includes the mandatory read instruction pointing at its guide.

### 4. Enforcement

The agent's conversation loop checks: did the agent read the guide before acting?

```python
# agent/guide_enforcer.py

class GuideEnforcer:
    """Ensures the agent reads its AGENT_GUIDE.md before acting."""

    def __init__(self, persona: str):
        self.guide_path = f"skills/personas/{persona}/AGENT_GUIDE.md"
        self.guide_read = False

    async def enforce(self, session: Session) -> None:
        """Check if the guide has been read this session."""
        if not self.guide_read:
            # Inject the guide content at the start of the first turn
            guide_content = await read_file(self.guide_path)
            session.inject_system_message(
                f"You must read and follow this routing guide:\n\n{guide_content}"
            )
            self.guide_read = True
```

Simple enforcement: if the first tool call in a session is NOT a file read of the guide, the agent is warned and the guide is injected directly.

## Files to create

```
skills/personas/nexus/
  AGENT_GUIDE.md              - NEXUS routing guide (decision tree, persona map)

skills/personas/warden/
  AGENT_GUIDE.md              - security escalation paths (stub)

skills/personas/echo/
  AGENT_GUIDE.md              - call escalation triggers (stub)

src/keprix/agent/
  guide_enforcer.py           - ensure guide is read before acting

src/keprix/personas/
  nexus.py                    - MODIFY: add mandatory guide instruction to system prompt
  base.py                     - MODIFY: add guide_path to persona base class

tests/agent/
  test_guide_enforcer.py
  test_nexus_routing.py       - verify routing decision tree matches persona map
```

## Acceptance criteria

- NEXUS's system prompt starts with the mandatory guide instruction. The instruction is the first line.
- On first turn, NEXUS reads AGENT_GUIDE.md before taking any action. If it does not, the guide is injected directly.
- The routing decision tree covers all 9 personas with clear trigger conditions.
- Routing a request to the wrong persona (e.g., sending a security audit to FORGE) is caught by the guide enforcer.
- Other personas (WARDEN, ECHO) have stub AGENT_GUIDE.md files with their domain-specific rules.
