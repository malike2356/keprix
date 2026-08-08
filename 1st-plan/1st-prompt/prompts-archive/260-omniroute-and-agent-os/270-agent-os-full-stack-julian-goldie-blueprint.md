# Keprix Prompt 270: Agent OS; Hermes-Equivalent Full Stack (From Julian Goldie's Blueprint)

## Status: DONE (Phases 1-5 shipped)

Phase 1 mapped onto existing Keprix modules (do not invent parallel stacks):

| Task | Status | Real path |
|------|--------|-----------|
| 1.1 Model-swappable | Done (pre-existing) | `keprix model` / `~/.keprix/config.yaml` |
| 1.2 Single-vault markdown | Done (pre-existing) | `src/keprix/vault/` |
| 1.3 Auto-capture | Done | `src/keprix/vault/capture.py` + web conversation hook |
| 1.4 One-command install | Done (pre-existing) | `scripts/install-curl.sh` |
| 1.5 Hello World workflow | Done | `keprix agent-os hello` → `agent_os/hello_world.py` |

Phase 2 core workflows:

| Task | Status | Real path |
|------|--------|-----------|
| 2.1 Content Series Generator | Done | `agent_os/workflows/content_series.py` + catalog `content-series` |
| 2.2 Memory System workflow | Done | `agent_os/workflows/memory_system.py` + catalog `memory-system` |
| 2.3 CRM Import/Clean | Done | `agent_os/workflows/crm_import.py` + catalog `crm-import` |
| 2.4 Sub-agent Kanban board | Done | `agent_os/workflow_kanban.py` (+ existing `keprix kanban`) |
| 2.5 Auto-skill writing | Done | `agent_os/auto_skill_writer.py` (hooked in agent-app runner) |

Phase 3 channels + dashboard:

| Task | Status | Real path |
|------|--------|-----------|
| 3.1 Discord | Done (pre-existing) | `plugins/platforms/discord/` |
| 3.2 Slack | Done (pre-existing) | `gateway/platforms/slack.py` |
| 3.3 Agent OS glass | Done | `/agent-os/glass` + `GET /api/agent-os/glass` |
| 3.4 Tokens per agent | Done | `GET /api/usage/breakdown/agent` + `/usage` |
| 3.5 Memory Galaxy | Done | `/memory/galaxy` on `GET /api/vault/graph` |

Phase 4 advanced workflows:

| Task | Status | Real path |
|------|--------|-----------|
| 4.1 Video Agent | Done | `workflows/video_agent.py` + catalog `video-agent` |
| 4.2 SEO Agent | Done | `workflows/seo_agent.py` + catalog `seo-agent` |
| 4.3 Outreach/Lead | Done | `workflows/outreach_agent.py` + catalog `outreach-agent` |
| 4.4 Onboarding Path | Done | `workflows/onboarding_path.py` + catalog `onboarding-path` |
| 4.5 Day 1/7/30 wizard | Done | `agent_os/milestones.py` + `GET /api/agent-os/milestones` |

Phase 5 polish + ship:

| Task | Status | Real path |
|------|--------|-----------|
| 5.1 Token minimization playbook | Done | `agent_os/token_playbook.py` + `keprix agent-os playbook` |
| 5.2 Server deploy script | Done | `scripts/deploy-server.sh` + `deploy/keprix.service` |
| 5.3 Managed hosting | Done | `scripts/deploy-managed.sh` + `fly.toml` |
| 5.4 Guardrails defaults | Done | `agent_os/guardrails.py` (workspace, approvals, vault backup) |
| 5.5 Error paste loop | Done | `workflows/error_paste.py` + catalog `error-paste` |

Docs: `docs/features/agent-os-phase5-polish.md`. Tests: `tests/agent_os/test_phase5_polish.py`.

## Source
YouTube: "Hermes Agent OS Just Got WAY More Powerful"; Julian Goldie, July 2026
Video ID: 5fATl0YqXbU

---

## Summary

Extract, adopt, and surpass every workflow, architectural decision, and operational principle from Julian Goldie's Agent OS blueprint. Build the equivalent inside Keprix; not as a clone, but as the superior implementation. The video reveals real-world production patterns from 4,000+ users. Keprix should absorb the good, improve the weak, and ship the result.

---

## The Agent OS Architecture (Julian's Stack)

```
┌─────────────────────────────────────────────────────────┐
│                    DASHBOARD                              │
│              (Visibility + Control Layer)                 │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              HERMES AGENT ENGINE                   │   │
│  │                                                    │   │
│  │  ┌─────────┐  ┌──────────┐  ┌────────────────┐   │   │
│  │  │  Model  │  │  Skills  │  │  Sub-Agents    │   │   │
│  │  │ Router  │  │  Auto-   │  │  (Kanban       │   │   │
│  │  │(swappable)│ │  Write   │  │  Board)        │   │   │
│  │  └─────────┘  └──────────┘  └────────────────┘   │   │
│  │                                                    │   │
│  │  Channels: Terminal · Telegram · Discord · Slack  │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                                │
│  ┌──────────────────────▼───────────────────────────┐   │
│  │              OBSIDIAN VAULT (Memory)               │   │
│  │                                                    │   │
│  │  ┌──────────┐  ┌──────────┐  ┌───────────────┐   │   │
│  │  │ Omi      │  │ Markdown │  │ Memory Galaxy │   │   │
│  │  │ Capture  │→ │ Files    │→ │ Visualization │   │   │
│  │  │(conversations │(local)   │  │               │   │   │
│  │  │ + screen) │  │          │  │               │   │   │
│  │  └──────────┘  └──────────┘  └───────────────┘   │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### The Memory Loop (THE KEY INSIGHT)

```
CAPTURE → STORE → READ → VISUALIZE
  │         │       │        │
  Omi    Obsidian  Hermes  Memory Galaxy
(open-   (local   (reads   (see what
source)  vault)   from it)  you know)
```

---

## Tech Stack to Implement in Keprix

### Core Engine
| Component | Julian's Choice | Keprix Equivalent | Action |
|-----------|----------------|-------------------|--------|
| Agent Runtime | Hermes (Nous Research) | Keprix IS the runtime | Done:  Keprix already is this |
| Model Router | Hermes `--model` flag | Keprix model config | Build swappable model system with single-command change |
| Channels | Terminal, Telegram, Discord, Slack | Build all four | Telegram exists; add Discord, Slack, terminal |
| Sub-Agents | Hermes delegate + Kanban | Keprix delegate + Kanban | Build Kanban board UI for agent task queue |
| Skills | Auto-write from execution | Port this | Agents should write their own skills from successful workflows |

### Memory
| Component | Julian's Choice | Keprix Equivalent | Action |
|-----------|----------------|-------------------|--------|
| Memory Store | Obsidian vault (local markdown) | File-based markdown vault | Build Obsidian-compatible vault reader |
| Memory Capture | Omi (open-source, captures conversations + screen) | Build equivalent | Auto-capture: every conversation → markdown note → vault |
| Memory Visualization | "Memory Galaxy" graph | Build in dashboard | Visual graph of knowledge connections |
| One Vault Rule | Single vault for ALL agents/projects | Enforce by default | Never split; one memory, all agents |

### Dashboard
| Component | Julian's Choice | Keprix Equivalent | Action |
|-----------|----------------|-------------------|--------|
| Agent OS Dashboard | Custom (in AI Profit Boardroom) | Build Keprix dashboard | Single pane of glass; all agents, memory, tasks visible |
| Token Monitoring | Token minimization playbook | Build into dashboard | Show token usage, cost, efficiency per agent |
| Kanban Board | Hermes Kanban | Build | Visual task board for agent work queues |

---

## Workflows to Build (The 7 Core Workflows)

### Workflow 1: Content Series Generator
```
INPUT: Topic + audience questions
  → Agent drafts hooks
  → Agent writes scripts
  → Agent generates captions
  → Agent maps cross-platform variants
OUTPUT: Full content series ready to publish

Use Case: One prompt → team of agents → real output
Key: Sub-agents run in parallel for each piece
```

### Workflow 2: Onboarding Path Builder
```
INPUT: Product/service description
  → Agent maps welcome sequence
  → Agent writes first-call prep
  → Agent builds system walkthrough
  → Agent creates day-1/day-7/day-30 checklist
OUTPUT: Complete onboarding experience

Use Case: New users land → instantly know what to do next
Key: Progressive disclosure; not all at once
```

### Workflow 3: Video Agent
```
INPUT: Topic
  → Agent generates script
  → Agent creates visual storyboard
  → Agent produces/edits video (or prepares for human)
  → Agent writes description + tags + thumbnail text
OUTPUT: Video ready to publish

Use Case: Automate the #1 time-sink (content creation)
Key: Agent does the planning + prep; human does final review
```

### Workflow 4: SEO Agent
```
INPUT: Keywords + website
  → Agent researches competitors
  → Agent generates content outline
  → Agent writes SEO-optimized article
  → Agent checks internal linking opportunities
  → Agent monitors rankings
OUTPUT: Published, ranking content

Note: Julian uses Open SEO (GitHub) + Claude Code for this
Key: Agent reads the repo, walks you through setup, fixes its own errors
```

### Workflow 5: Memory System
```
INPUT: Daily conversations + screen context
  → Omi-like capture (auto)
  → Convert to structured markdown notes
  → Store in vault
  → Index for search
  → Visualize connections
OUTPUT: Agent remembers everything across sessions

Key: This is the multiplier. Without it, agents have amnesia.
Loop: Capture → Store → Read → Visualize
```

### Workflow 6: Outreach/Lead Agent
```
INPUT: Target audience + offer
  → Agent plans content calendar
  → Agent writes hooks for each platform
  → Agent sequences follow-ups
  → Agent maps next steps per lead
OUTPUT: Full lead generation + nurturing system

Use Case: Bring right people into your ecosystem
Key: All from one workflow; not separate tools
```

### Workflow 7: CRM Import/Clean Agent
```
INPUT: Messy spreadsheet/CSV
  → Agent cleans data (deduplicate, fix columns, normalize)
  → Agent maps columns to CRM field names
  → Agent validates against CRM schema
  → Agent imports
OUTPUT: Clean data in CRM

Use Case: GoHighLevel, HubSpot, Salesforce imports
Key: Most import failures = bad file, not bad CRM. Agent fixes the file first.
```

---

## Operational Principles (From the Video)

### Principle 1: System Over Model
> "The model was never the problem. The system around it was."
> "A better brain in a broken body still trips over its own feet."

**Keprix must:** Make the model swappable with a single command. The system stays. The model is just a part you can replace. Build Grok 4.5, GPT 5.6 (Soul/Terra/Luna), Claude support; and make switching trivial.

### Principle 2: One Vault, One Memory
> "Keep one Obsidian vault, not five, not one per project."

**Keprix must:** Enforce single memory store. All agents read from one place. Multiple vaults = agents see half the story and burn tokens hunting for the other half. One vault = shared brain.

### Principle 3: Fewer Moving Parts
> "Fewer moving parts is the whole game."

**Keprix must:** Collapse the stack. Don't make users stitch together 5 tools. Hermes (engine) + Obsidian (memory) + Dashboard (visibility) = done. Don't add n8n unless it's just a connector. Don't add Paperclip/Claude Code multi-agent unless the user can name the specific use case.

### Principle 4: Start Small, Get One Working
> "Start with one workflow, not 10. Get it working end to end."

**Keprix must:** Ship with one killer workflow pre-built. New users run one command → get a working result → THEN explore. Don't overwhelm with options.

### Principle 5: Guardrails Before Keys
> "Don't hand them the keys to everything on day one. Keep them in one folder. Give them one job. Read the plan before you approve it."

**Keprix must:** Default to restricted. Agents start in one workspace folder. Approval required for destructive actions. Vault auto-backed up. Never paste API keys into scripts the user hasn't read.

### Principle 6: Token Efficiency
> "Use a coding plan instead of raw API keys, so your token use stays predictable and your agent doesn't stop halfway through a job."

**Keprix must:** Build token budgeting. Predictable costs. Warn before overage. Show token usage per agent. The "Token Minimization Playbook" from the video has ~10 techniques; adopt them all.

### Principle 7: AI Inside Existing Business
> "Don't start a new AI business. Put AI inside the business you already have."

**Keprix must:** Position for augmentation, not replacement. Target existing businesses with known problems. Not a new thing to learn; a thing that fixes what's already broken.

### Principle 8: Local First, Server When Ready
> "If you're learning, run it locally. Move it onto a server only when you genuinely need it running while you sleep."

**Keprix must:** One-command local install. Server deployment is a conscious upgrade, not a requirement. Don't force infrastructure.

### Principle 9: Agents Do Thinking, Tools Do Moving
> "I let the agent do the thinking and I let n8n move the finished thing from A to B. If a workflow needs 20 nodes just to survive, it's going to break on you."

**Keprix must:** Own the reasoning. External tools (n8n, Zapier) are dumb pipes. Complex logic stays in the agent.

### Principle 10: One Agent Done Right > Five Half-Built
> "One agent, done properly, beats five agents you can't explain."

**Keprix must:** Ship depth, not breadth. One agent that actually works end-to-end > a marketplace of half-baked templates.

---

## Hosting Strategy (Three Tiers; from the Video)

| Tier | When | Keprix Must |
|------|------|-------------|
| **Local** | Learning, building, testing | One-command install. Works immediately. Free. |
| **Small Server** | Needs 24/7 operation | Simple deploy script. VPS-friendly. Runs while you sleep. |
| **Managed Host** | Don't want to manage infra | One-click deploy. Automatic updates. Backups included. |

> "Don't set up infrastructure you're not using yet."

---

## The 30-Day Roadmap (Adopt from Julian)

| Day | What | Keprix Implements |
|-----|------|-------------------|
| **Day 1** | Install + first prompt | One-command install. Pre-built "Hello World" workflow. First result in 5 minutes. |
| **Day 7** | Memory wired + 3 workflows running | Obsidian vault connected. Content, SEO, and CRM workflows working. |
| **Day 30** | Full Agent OS running | Dashboard live. Sub-agents deployed. Token budget dialed. Everything visible from one screen. |

---

## Tech Decisions to Adopt

### Done:  Adopt Directly
| Decision | Why |
|----------|-----|
| Markdown-based memory (file system) | Portable, local, nothing locked away, agents can read/write directly |
| Single vault | Shared brain = smarter agents = fewer tokens burned |
| Model-swappable architecture | Locking to one model is a trap. Grok 4.5 Jan 2026, GPT 5.6 Feb 2026; model changes are weekly. |
| Channels: Terminal + Telegram + Discord + Slack | Cover all surfaces. Start with terminal + Telegram (already have). |
| Sub-agent Kanban board | Visual task management. Agents pick up, move, complete. User watches. |
| Auto-skill writing | Agent succeeds at a task → writes the skill for next time. Compounds. |
| Error paste loop | Agent reads docs → runs → breaks → user pastes error → agent fixes → repeat. No manual debugging. |

###  Improve (Weak Points in Julian's Stack)
| Julian's Approach | Keprix Improvement |
|-------------------|-------------------|
| Obsidian is a separate install | Build vault reader natively; no separate app needed |
| Omi captures separately → Obsidian | Build capture directly into Keprix; every conversation auto-saved |
| Dashboard is custom (AI Profit Boardroom) | Build native Keprix dashboard; not a bolt-on |
| Token monitoring is a separate playbook | Embed token tracking in every agent view |
| 30-day roadmap is a PDF | Interactive onboarding wizard with progress tracking |
| Agent OS "zip file" delivery | One-command install + guided setup |

### Failed:  Skip (Anti-Patterns)
| Thing | Why Skip |
|-------|----------|
| Multiple vaults | Breaks shared memory. One vault only. |
| n8n for thinking | Use only as connector. Agent owns the logic. |
| Paperclip/Claude Code multi-agent without a named use case | Complexity for complexity's sake. User must name the use case first. |
| Starting a new AI business | Put AI in existing business. Keprix augments, doesn't require a pivot. |
| Hand-editing files you don't understand | Let the agent read the docs and do it. Paste errors back. |

---

## Task List; Build Order

### Phase 1: Foundation (Days 1-7)
- [x] **Task 1.1**: Build model-swappable architecture; single config change switches Grok ↔ GPT ↔ Claude
- [x] **Task 1.2**: Build single-vault markdown memory system; read/write/search
- [x] **Task 1.3**: Build auto-capture; every conversation → markdown note in vault
- [x] **Task 1.4**: One-command local install (`curl ... | bash` or `pip install keprix`)
- [x] **Task 1.5**: Pre-built "Hello World" workflow; first result in 5 minutes

### Phase 2: Core Workflows (Days 8-14)
- [x] **Task 2.1**: Content Series Generator workflow (Workflow 1)
- [x] **Task 2.2**: Memory System workflow; capture → store → read → visualize (Workflow 5)
- [x] **Task 2.3**: CRM Import/Clean workflow (Workflow 7)
- [x] **Task 2.4**: Sub-agent system with Kanban board UI
- [x] **Task 2.5**: Auto-skill writing; agent writes skill after successful workflow

### Phase 3: Channels + Dashboard (Days 15-21)
- [x] **Task 3.1**: Discord channel adapter
- [x] **Task 3.2**: Slack channel adapter
- [x] **Task 3.3**: Native Keprix dashboard; all agents, memory, tasks visible
- [x] **Task 3.4**: Token tracking per agent; cost, usage, efficiency
- [x] **Task 3.5**: Memory Galaxy visualization; see the shape of what you know

### Phase 4: Advanced Workflows (Days 22-30)
- [x] **Task 4.1**: Video Agent workflow (Workflow 3)
- [x] **Task 4.2**: SEO Agent workflow (Workflow 4)
- [x] **Task 4.3**: Outreach/Lead Agent workflow (Workflow 6)
- [x] **Task 4.4**: Onboarding Path Builder workflow (Workflow 2)
- [x] **Task 4.5**: Interactive onboarding wizard with progress tracking (day 1/7/30)

### Phase 5: Polish + Ship (Days 31+)
- [x] **Task 5.1**: Token minimization playbook; 10 techniques embedded
- [x] **Task 5.2**: Server deploy script; VPS-friendly
- [x] **Task 5.3**: Managed hosting option; one-click deploy
- [x] **Task 5.4**: Guardrails default; restricted workspace, approval gates, auto-backup
- [x] **Task 5.5**: Error paste loop; built-in: agent reads docs → runs → breaks → user pastes → agent fixes

---

## Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `keprix/config/models.yaml` | Model-swappable config; single command changes provider |
| 2 | `keprix/memory/vault.py` | Markdown vault reader/writer/search |
| 3 | `keprix/memory/capture.py` | Auto-capture conversations → vault notes |
| 4 | `keprix/memory/visualizer.py` | Memory Galaxy graph builder |
| 5 | `keprix/dashboard/server.py` | Native Keprix dashboard backend |
| 6 | `keprix/dashboard/frontend/` | Dashboard UI; agents, memory, tasks, tokens |
| 7 | `keprix/workflows/content_series.py` | Workflow 1: Content Series Generator |
| 8 | `keprix/workflows/onboarding.py` | Workflow 2: Onboarding Path Builder |
| 9 | `keprix/workflows/video_agent.py` | Workflow 3: Video Agent |
| 10 | `keprix/workflows/seo_agent.py` | Workflow 4: SEO Agent |
| 11 | `keprix/workflows/memory_system.py` | Workflow 5: Memory System |
| 12 | `keprix/workflows/outreach_agent.py` | Workflow 6: Outreach/Lead Agent |
| 13 | `keprix/workflows/crm_import.py` | Workflow 7: CRM Import/Clean |
| 14 | `keprix/kanban/board.py` | Sub-agent Kanban board |
| 15 | `keprix/skills/auto_writer.py` | Auto-skill writer; agents document their own workflows |
| 16 | `keprix/channels/discord_adapter.py` | Discord channel integration |
| 17 | `keprix/channels/slack_adapter.py` | Slack channel integration |
| 18 | `keprix/tokens/tracker.py` | Token usage/cost/efficiency per agent |
| 19 | `keprix/deploy/install.sh` | One-command install script |
| 20 | `keprix/deploy/server.sh` | Server deploy script |
| 21 | `keprix/onboarding/wizard.py` | Interactive onboarding wizard (day 1/7/30) |
| 22 | `keprix/guardrails/workspace.py` | Restricted workspace; agents start in one folder |
| 23 | `keprix/guardrails/approval.py` | Approval gates for destructive actions |
| 24 | `keprix/guardrails/backup.py` | Auto-backup vault before agent writes |

---

## Model Support (To Build)

| Model | Provider | Why |
|-------|----------|-----|
| Grok 4.5 | xAI | "Opus class, built for coding and agent work, 4x fewer output tokens than Opus 4.8" |
| GPT 5.6 Soul | OpenAI | "Topping coding charts right now"; heavy tier |
| GPT 5.6 Terra | OpenAI | Everyday tier |
| GPT 5.6 Luna | OpenAI | Fast, light tier |
| Claude Fable 5 | Anthropic | "Still the one to beat on plenty of benchmarks" |
| DeepSeek V4 | DeepSeek | Currently used in Keprix |

---

## Acceptance Criteria

- [x] Model-swappable: single config change switches provider
- [x] Single vault: all agents read/write to one markdown directory
- [x] Auto-capture: every conversation saved as note
- [x] Memory visualization: graph showing knowledge connections
- [x] 7 workflows built and working
- [x] Kanban board: agents pick up, move, complete tasks visually
- [x] Auto-skill writing: agents document successful workflows
- [x] Channels: terminal + Telegram + Discord + Slack
- [x] Dashboard: all agents, memory, tasks visible from one screen
- [x] Token tracking per agent
- [x] One-command local install
- [x] Server deploy script
- [x] Guardrails: restricted workspace, approval gates, auto-backup
- [x] Interactive onboarding wizard with day 1/7/30 milestones
- [x] Error paste loop: agent reads → runs → breaks → user pastes → agent fixes

---

## Reference

Video: https://youtu.be/5fATl0YqXbU
Creator: Julian Goldie (digital avatar)
Product: AI Profit Boardroom (4,000+ members)
Transcript: extracted and analyzed
