# Agent OS Phase 4 advanced workflows

## Commands

```bash
keprix agent-os workflow video --topic "Agent OS" --audience operators --minutes 8
keprix agent-os workflow seo --keywords "agent os, memory vault" --website https://example.com
keprix agent-os workflow outreach --audience "agency owners" --offer "a free install"
keprix agent-os workflow onboarding-path --product "Keprix" --audience "new users"
keprix agent-os milestones
```

## Apps

Install from `/agent-apps`:

- Video Agent
- SEO Agent
- Outreach Lead Agent
- Onboarding Path Builder

## Day 1 / 7 / 30 wizard

UI: `/agent-os/onboarding` (milestone cards + activation checklist).

`GET /api/agent-os/milestones` (also embedded in `/api/agent-os/onboarding`) tracks progress against the three roadmap milestones.
