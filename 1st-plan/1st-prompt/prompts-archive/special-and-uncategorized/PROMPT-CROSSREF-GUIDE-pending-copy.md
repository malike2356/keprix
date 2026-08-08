# Keprix Prompt Cross-Reference Guide

Use this when editing prompt bodies. Filename number is execution order. H1 headers
must match filenames. If body text disagrees with the filename number, the filename
wins.

## Authoritative Prompt Map

| Range | Meaning |
| --- | --- |
| 00a | Product vision and expanded agent consolidation map |
| 00b | Full build scope and build order |
| 00 | Project setup, architecture, and developer access |
| 01-02 | Foundation: developer identity and security hardening (completed; see `prompts-archive/`) |
| 03-05, 07 | Hermes spine (archived: superseded-by-hermes-clone) |
| 06 | Memory and RAG (Keprix pgvector/ChromaDB layers still active) |
| 08-16 | Secure workspace: vault, credentials, documents, email, contacts, research, automation |
| 13, 15, 17, 43 | Also archived under superseded-by-hermes-clone |
| 18-27 | API, SDK, frontend, slash commands, notifications, mobile, hardening, localization |
| 28-46 | Self-building, project builder, domain packs, evals, distribution, boundaries, backup, migration, ambient events |
| 47-50 | African language localization layer |
| 51-59 | Core reference-agent adoption pack |
| 60-73 | Expanded reference-agent adoption pack |
| 74-83 | Research workspace and statistical tools |
| 84-95 | Opportunity Engine |
| 96-106 | Agent personas |
| 107-113 | Human review, exports, GDPR, legal gates, clinical gates, outbound notifications |
| 114-115 | Standalone Keprix marketing site |

## Common Reference Numbers

| Capability | Prompt |
| --- | --- |
| Durable playbook runtime | 51 |
| Crews and flows | 52 |
| Browser action engine | 53 |
| Data analytics code workspace | 54 |
| Self-coding patch trajectories | 55 |
| Tool library adapter pack | 56 |
| Agent evals and trace observability | 57 |
| Multi-agent messaging and studio | 58 |
| Core adoption release map | 59 |
| Expanded reference-agent audit | 60 |
| OpenHands-style control center | 61 |
| Aider-style git-native coding UX | 62 |
| browser-use-style browser harness | 63 |
| smolagents-style code agent and hub tools | 64 |
| OpenAI Agents-style handoffs, guardrails, tracing, and realtime | 65 |
| Pydantic AI-style typed agents | 66 |
| Google ADK-style lifecycle and workflow app | 67 |
| Semantic Kernel-style plugin and planner interop | 68 |
| LlamaIndex-style document agents and RAG | 69 |
| Mastra-style TypeScript workflows | 70 |
| Agno-style interfaces and auto-improvement | 71 |
| Haystack-style production RAG | 72 |
| Expanded adoption release map | 73 |
| Opportunity Engine architecture | 84 |
| NEXUS persona base and registry | 96 |

## Working Directory

All implementation prompts target:

```text
/opt/lampp/htdocs/verlox/keprix/keprix/
```

Marketing prompts target:

```text
/opt/lampp/htdocs/verlox/keprix/marketing/sites/keprix/
```

## Reference Clone Path

Reference agents live under:

```text
/opt/lampp/htdocs/verlox/keprix/planning/agents-to-adopt/
```

Do not edit cloned upstream projects unless the task explicitly says to update the
local reference copy. Active Keprix prompts live directly in `planning/prompts/`.
