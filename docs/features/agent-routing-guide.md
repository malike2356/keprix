# Persona AGENT_GUIDE routing

OpenMontage-style mandatory routing guides for Keprix personas.

## What shipped

- `skills/personas/nexus/AGENT_GUIDE.md`: NEXUS decision tree and persona map
- `skills/personas/warden/AGENT_GUIDE.md`: security escalation stub
- `skills/personas/echo/AGENT_GUIDE.md`: call escalation stub
- `agent/guide_enforcer.py`: inject guide on session start; soft-block first
  non-guide tool; catch obvious wrong-persona routes
- NEXUS / WARDEN / ECHO system prompts start with a `**MANDATORY: Read ...**` line

## Behaviour

1. Agent init injects the guide into `ephemeral_system_prompt` when
   `agent.guide_enforce` is true (default).
2. If the first tool call is not a read of `AGENT_GUIDE.md`, the executor
   returns a guide_enforcer warning and injects the guide content.
3. `GuideEnforcer.check_routing_mismatch` flags cases such as sending a
   security audit to FORGE instead of WARDEN.

## Note on CODEX

In Keprix, CODEX is the legal specialist (contracts, NDAs). The NEXUS guide
matches the live roster, not a "code-only" CODEX label.
