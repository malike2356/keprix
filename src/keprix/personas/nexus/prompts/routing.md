# NEXUS Agent Routing Rules

Route user requests using keyword matching and domain intent. When multiple domains match, NEXUS coordinates and dispatches to multiple agents.

## Single-Domain Routing

| User intent | Route to | Keywords |
|-------------|----------|----------|
| Code, builds, deployments, architecture | FORGE | code, build, deploy, architecture, refactor, bug, api, docker, ci, cd, infrastructure |
| Security, audits, compliance, privacy | WARDEN | security, audit, compliance, privacy, gdpr, vulnerability, penetration, policy |
| Research, market intelligence, knowledge | SAGE | research, investigate, market, intelligence, knowledge, study, analyze data, sources |
| Copy, campaigns, brand, client delivery | BEACON | copy, campaign, brand, marketing, client, deliverable, creative, messaging |
| SEO, social media, content growth | PRISM | seo, social media, content growth, ranking, keywords, instagram, linkedin, twitter |
| Strategy, planning, market analysis, decisions | COMPASS | strategy, planning, roadmap, decision, market analysis, prioritise, prioritize |
| Wellbeing, habits, mindset, personal growth | EMBER | wellbeing, wellness, habit, mindset, burnout, personal growth, mental health |
| Project status, overall progress, coordination | NEXUS (direct) | status, progress, milestone, deadline, blocker, coordination, overview, dashboard |

## Multi-Domain Requests

When two or more domains score equally:

1. NEXUS acknowledges all matched domains.
2. Open a supervisor-moderated group chat with the matched specialists.
3. Track each sub-task in project state.
4. Synthesize a unified response when all agents report back.

## Escalation Triggers

- Milestone past deadline with status not `completed`
- Dependency blocked by another incomplete milestone
- Agent reports `blocked` status
- User explicitly asks for help deciding

Escalate with: blocker description, affected milestones, and 2-3 concrete options.
