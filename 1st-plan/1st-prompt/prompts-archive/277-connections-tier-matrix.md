# Keprix - Prompt 277: Connections tier matrix

**Series:** Nate Herk AIOS adoption **274-279**  
**Master reference:** `../prompts-archive/ref-273-nate-herk-aios-adoption-master-reference.md`  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

Archived after implementation on 2026-07-09.

## Summary

Built the Agent OS connections tier matrix:

- `connections.md` and `connections.json` model for seven tier-1 domains.
- Parser, renderer, service, API, CLI, and `/agent-os/connections` wizard.
- Day-2 `connections.domain_live` onboarding event.
- AI service account documentation.
- Suggested tool map including `google-workspace` for prompt 279.

## Acceptance

- `init-template` creates valid `connections.md` with all seven domains.
- Parser round-trips markdown to model and back.
- Priority wizard returns three ranked domains with rationale strings.
- Four C's maturity scorer reads live domains.
- Agent OS day-2 checklist completes when a domain goes live.
