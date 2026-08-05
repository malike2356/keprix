# keprix - Prompt 00a: Product Vision and Agent Consolidation Map

## Purpose

This prompt is **reference only**. Read it before Prompt 00. It defines what keprix is,
which agents it consolidates, how Hermes becomes the spine, where Carina features fit,
and how Scout connects as a paid optional layer.

Every other prompt in this series must align with this map.

---

## What keprix Is

keprix is a single self-hosted AI agent OS that consolidates the best capabilities from
an expanded set of researched agent platforms into one MIT-licensed distribution, plus keprix-only
capabilities that none of the sources provide alone.

It is not a fork of any one project. It is a deliberate synthesis:

| Layer | Role |
| --- | --- |
| **Spine (clone and rename)** | Hermes Agent provides the conversation loop, tool dispatch, context engine, CLI, and provider routing. Port verbatim, then rename every Hermes identifier to keprix. |
| **Platform features (rebuild with boundaries)** | Carina commercial stack (`core.carinaai.uk`, workspace UI patterns) supplies memory, RAG, workspace, integrations, and operator UX lessons. Rebuild in keprix; never copy secrets, tenant data, or commercial keys. |
| **Channel and mobile (adopt patterns)** | OpenClaw supplies multi-channel gateway patterns and mobile-facing flows. |
| **Research workspace (merge)** | Odysseus supplies research pipeline and self-hosted search patterns. |
| **Orchestration pack (adopt concepts)** | LangGraph, CrewAI, AutoGen, Mastra, Google ADK, and OpenAI Agents SDK supply durable playbooks, crews/flows, lifecycle, handoffs, and multi-agent messaging. |
| **Specialist engines (adopt concepts)** | LaVague and browser-use (browser), TaskWeaver (analytics/code workspace), SWE-agent, Aider, and OpenHands (coding and control center) become governed keprix modules. |
| **Typed, plugin, and data layers (adopt concepts)** | Pydantic AI, Semantic Kernel, LlamaIndex, Haystack, smolagents, and Agno supply typed agents, plugin contracts, RAG pipelines, code agents, interfaces, and improvement loops. |
| **keprix-only** | Mutation engine (Prompt 28): synthesize, sandbox, approve, and install new tools live. Opportunity Engine (Prompts 84-95). |

---

## The Researched Agents

Reference clones live in `planning/agents-to-adopt/`.

| # | Agent | Upstream focus | keprix adoption | Primary prompt(s) |
| --- | --- | --- | --- | --- |
| 1 | **Hermes Agent** | Personal AI agent, CLI, tool loop | **Full port and rename** (spine) | 03, 04, 05, 07 |
| 2 | **OpenClaw** | Multi-channel gateway, mobile | Channel adapters, mobile patterns | 11, 18, 31 |
| 3 | **Odysseus** | Research, SearXNG, workspace | Research pipeline, search stack | 06, 09, 12, 40 |
| 4 | **LangGraph** | Stateful durable workflows | Playbook runtime (no hard LangGraph dep) | 51 |
| 5 | **CrewAI** | Role-based crews and flows | Agent teams, tool adapter pack | 52, 56 |
| 6 | **AutoGen** | Multi-agent conversation | Agent Studio, messaging bus | 58 |
| 7 | **LaVague** | Browser automation | Browser action engine | 53 |
| 8 | **TaskWeaver** | Data analytics code agent | Analytics workspace | 54 |
| 9 | **SWE-agent** | Issue-to-patch trajectories | Governed self-coding paths | 28, 55 |
| 10 | **Carina core** | Managed platform runtime | Memory, RAG, vault, workspace, API patterns | 06, 08, 09, 16, 45 |
| 11 | **OpenHands** | Agent control center and software engineering workspace | Agent servers, automation triggers, control center | 61 |
| 12 | **Aider** | Git-native coding assistant | Repo map, git workflow, lint and test loop, watch mode | 62 |
| 13 | **browser-use** | Browser harness for agents | Browser profiles, sessions, skills, benchmarks | 63 |
| 14 | **smolagents** | Code agents and hub tools | Code-agent mode, sandbox providers, tool collections | 64 |
| 15 | **OpenAI Agents SDK** | Handoffs, guardrails, tracing, realtime | Agent runtime, realtime lane, trace viewer | 65 |
| 16 | **Pydantic AI** | Typed production agents | Dependency injection, schema validation, typed outputs | 66 |
| 17 | **Google ADK** | Agent app lifecycle and workflow runner | Agent app manifests, lifecycle hooks, runners | 67 |
| 18 | **Semantic Kernel** | Plugin and planner architecture | Plugin contracts, memory providers, interoperability | 68 |
| 19 | **LlamaIndex** | Document agents and indexing | Document parsing, structured extraction, query engines | 69 |
| 20 | **Mastra** | TypeScript agents and workflows | TS SDK, workflow developer UX, memory and evals | 70 |
| 21 | **Agno** | Agent interfaces and improvement loop | Interfaces, A2A, AG-UI, auto-improvement | 71 |
| 22 | **Haystack** | Production RAG pipelines | Pipeline components, routing, retrieval evaluation | 72 |

**Aiva** (customer product on Carina) is a **boundary reference**, not an eleventh spine.
Use Prompt 29 to extract public-compatible patterns without copying commercial-only code.

---

## Hermes as Spine: Clone, Rename, Do Not Refactor

Prompt 03 is explicit: port Hermes agent core **verbatim**, apply the rename table, wire
into keprix. Do not refactor logic in the first pass. Do not leave Hermes strings in
user-visible output, env vars, paths, or module names.

| Find | Replace |
| --- | --- |
| `hermes` (identifier/string) | `keprix` |
| `Hermes` | `keprix` |
| `HERMES` | `keprix` |
| `hermes_state` | `keprix_state` |
| `hermes_constants` | `keprix_constants` |
| `~/.hermes/` | `~/.keprix/` |
| `HERMES_` (env prefix) | `keprix_` |

Source tree:

```text
planning/agents-to-adopt/hermes-agent/
```

Output tree:

```text
keprix/backend/agent/
keprix/backend/cli/
```

After Prompt 40 (rebrand sweep), no operator-facing surface may reference Hermes,
OpenClaw, Odysseus, or upstream repo URLs.

---

## Carina Features: What keprix Takes

Carina lives at `/opt/lampp/htdocs/verlox/carina/`. keprix adopts **behavior and
architecture**, not branding or commercial infrastructure.

| Carina capability | keprix target | Notes |
| --- | --- | --- |
| pgvector RAG and hybrid search | Prompt 06 | Self-hosted only |
| Credential vault and redaction | Prompt 08 | No `keys.carinaai.uk` |
| Workspace (docs, notes, calendar) | Prompt 10 | Rebuild, do not copy tenant schemas |
| Provider router and cost tracking | Prompt 04 | Hermes router extended with Carina lessons |
| REST/WebSocket API and observability | Prompt 18 | OpenAPI, traces, health |
| UI shell and connector patterns | Prompts 21-22 | Reference `app.carinaai.uk` layouts; Keprix branding only |
| Skills and plugin packs | Prompt 07 | Community pack schema |
| MCP and integration registry | Prompt 17 | |

**Never port into keprix:** Aiva Keys, managed SaaS billing, multi-tenant white-label,
blockchain trust attestation, in-app Aiva upsell, or `keys.carinaai.uk`.

Prompt 29 owns the formal extraction workflow and classification for every Carina/Aiva idea.

---

## Scout: Optional, Paid, Never Bundled

[Labyrinth Scout](https://labyrinthscout.com) is governance for AI systems: kill switches,
audit trails, policy enforcement, and trust anchoring. It is a **separate paid product**.

| Product | Scout |
| --- | --- |
| keprix (MIT, self-hosted) | Optional connector at **full price**. Not included. |
| Petraclus Pro/Team | Marketing discount (see Petraclus prompts). |
| Aiva (commercial) | Included with subscription. |

keprix must:

- Ship the connector (Prompt 30) so operators **can** connect Scout.
- Never bundle Scout, never imply keprix is insecure without it, never offer Scout free in keprix UI.
- Store Scout API keys in the vault (Prompt 08), not plaintext config.
- Surface governance settings only on `/settings/governance`, not as global nag banners.

---

## keprix-Only Differentiators

These are not ports. They define why keprix exists beyond consolidation:

1. **Mutation engine** (Prompt 28): detect tool gaps, synthesize tools, sandbox, approve, install live.
2. **Opportunity Engine** (Prompts 84-95): market discovery, validation, offer building, launch orchestration playbooks.
3. **Unified adoption releases** (Prompts 59 and 73): one navigation model, shared approval, trace, vault, and policy model across all adopted modules.

---

## Downstream products (built on keprix)

Vertical apps under `keprix-projects/` consume keprix via SDK or bundled Docker image.
They do not fork the keprix codebase.

| Priority | Product | Role |
| --- | --- | --- |
| 1 | **Petraclus** | Cyber workspace; official keprix image as AI backbone |
| 2 | **AbbiS** | Borehole industry SaaS; per-stakeholder AI on keprix |
| 3 | Fleetz | Fleet tracking (planned) |
| 4 | NHS / COMPASS | Clinical safety DevSecOps copilot (planned) |

See `keprix-projects/README.md` for integration rules and minimum keprix surface
required before Petraclus and AbbiS ship.

---

## Build Order Summary

```text
00a  This vision (read first)
00b  Full build scope and build order
00   Project setup and architecture
01-07 Foundation (Hermes spine + core platform)
08-16 Secure workspace, communication, research, automation, self-configuration
17-27 API, SDK, product shell, mobile, hardening, localization
28-46 Self-building, distribution, boundaries, backup, migration, ambient events
47-50 African language localization layer
51-59 Core reference-agent adoption pack
60-73 Expanded reference-agent DNA pack
74-83 Research workspace and statistical tools
84-95 Opportunity Engine
96-106 Agent personas
107-113 Safety, regulated workflows, and external output
114-115 Standalone marketing site
```

Cyber-only prompts were moved out of the active Keprix prompt order. Do not reintroduce
Petraclus offensive tooling, SIEM, forensics, or threat workflows into Keprix core.

---

## Adoption Rules (All Sources)

From `planning/agents-to-adopt/REUSE-NOTICE.md` and `BRAND-BOUNDARY.md`:

- Adopt **behavior**, not upstream wording.
- Rewrite prompts, labels, comments, UI copy, and docs in keprix voice.
- Keep only text required by licence, API, protocol, or file format.
- If copied text reads like the source project, rewrite before shipping.
- Never use "Carina keprix", "Powered by Carina" on keprix surfaces, or Carina env prefixes.
- "Sponsored by Carina" is allowed on keprix README/site only.

---

## Acceptance Criteria (for this document)

- A new contributor can read 00a and understand: spine (Hermes), platform (Carina), expanded reference-agent set, Scout boundary, and Mutation differentiator.
- Prompt 03, 37, 38, 59, and 73 cross-reference this file.
- `planning/prompts/README.md` lists the full build order from 00 through 115.
- All working-directory paths in active implementation prompts point to `/opt/lampp/htdocs/verlox/keprix/keprix/`.
- All reference-agent paths use `planning/agents-to-adopt/<agent>/`.
