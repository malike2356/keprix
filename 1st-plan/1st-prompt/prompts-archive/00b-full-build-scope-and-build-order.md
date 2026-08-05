# keprix - Prompt 00b: Full Build Scope and Build Order

## Purpose

This prompt defines the build order for the full Keprix prompt library. It replaces
the earlier MVP cut-line approach. Every prompt in the active prompt set is intended
to be built unless it has already been verified and archived.

Read `00a-product-vision-and-agent-consolidation-map.md` first. Read this file
before starting implementation so prompts are executed in dependency order rather
than by whichever file looks interesting first.

## Rule

Build in numeric order. Do not skip a prompt because older notes used launch-cut
language. Those labels are no longer authoritative. The active prompt number is
the execution order.

The only exception is a prompt that has already been implemented, tested, and
archived into `prompts-archive/`.

## Product Boundaries

Keprix is the open-source agent OS. Petraclus, AbbiS, Fleetz, and COMPASS are
products built on Keprix. Scout is a separate paid governance product with a
connector.

Keep these boundaries while building:

| Area | Belongs in |
| --- | --- |
| Agent runtime, tools, memory, RAG, workspace, prompts, SDK, localization | Keprix |
| Cyber workflows, offensive tooling, SIEM, forensics, target authorization | Petraclus |
| Borehole business workflows and product-specific Ghana localization | AbbiS |
| Kill switches, attestation, enterprise governance, paid trust layer | Scout connector, not bundled core |
| Managed customer subscriptions, Aiva employees, Carina SaaS billing | Carina and Aiva, not Keprix |

## Full Build Order

### Phase 0: Orientation and Foundation

These prompts define what Keprix is, establish the repository, and port the spine.

| Order | Prompt | Status |
| --- | --- | --- |
| 00a | Product vision and agent consolidation map | Active |
| 00b | Full build scope and build order | Active |
| 00 | Project setup, architecture, and developer access | Active |
| 01 | Developer identity and local access | Completed: `prompts-archive/` |
| 02 | Security foundation and platform hardening | Completed: `prompts-archive/` |
| 03 | Core agent engine | Archived: superseded-*.md (Hermes clone) |
| 04 | LLM providers and routing | Archived: superseded-*.md (Hermes clone) |
| 05 | Tools and terminal execution | Archived: superseded-*.md (Hermes clone) |
| 06 | Memory and RAG | Active (pgvector/ChromaDB layers still needed) |
| 07 | Skills and plugin system | Archived: superseded-*.md (Hermes clone) |

### Phase 1: Secure Workspace

This phase gives Keprix useful local work capability before advanced orchestration.

| Order | Prompt |
| --- | --- |
| 08 | Vault, credentials, and secrets |
| 09 | Agent-managed credential setup |
| 10 | Workspace documents, notes, and calendar |
| 11 | Email integration |
| 12 | Contact manager and sync |
| 13 | Messaging gateway | Archived: superseded-*.md (Hermes clone) |
| 14 | Deep research and playbook |
| 15 | Cron automation and scheduled tasks | Archived: superseded-*.md (Hermes clone) |
| 16 | Self-configuration |

### Phase 2: API, SDK, Product Shell, and Hardening

This phase makes the system usable by developers, products, and operators.

| Order | Prompt | Status |
| --- | --- | --- |
| 17 | MCP, ACP, and integrations | Archived: superseded-*.md (Hermes clone) |
| 18 | API surface and observability | Active |
| 19 | OpenAI-compatible public API and developer platform |
| 20 | App foundation SDK |
| 21 | Frontend UI and launchers |
| 22 | Unified UI/UX design system and app shell |
| 23 | Slash commands |
| 24 | Notifications, inbox, alert routing, and escalations |
| 25 | Mobile native apps |
| 26 | Keprix agent hardening |
| 27 | Localization, language, and voice |

### Phase 3: Self-Building, Distribution, Boundaries, and Operations

This phase turns Keprix from a capable agent into a buildable platform.

| Order | Prompt |
| --- | --- |
| 28 | Keprix self-coding agent |
| 29 | Project builder and monorepo |
| 30 | Domain knowledge pack factory |
| 31 | Benchmarks, evals, and quality regression harness |
| 32 | Combined data, ML, and research workspace architecture |
| 33 | Installer and zero-to-running |
| 34 | Documentation site and landing page |
| 35 | Community infrastructure and contribution guide |
| 36 | Hub, marketplace, packs, and template distribution |
| 37 | Aiva-to-Keprix feature extraction and boundary map |
| 38 | Scout governance bridge |
| 39 | Support, incident communications, and customer success |
| 40 | Rebranding and productization |
| 41 | Hot backup and restore |
| 42 | Agent migration manifest |
| 43 | Coding posture detection | Archived: superseded-*.md (Hermes clone) |
| 44 | Research task registry |
| 45 | Ambient room events |
| 46 | Voice wake words |

### Phase 4: African Language Localization

These prompts build the reusable localization layer. AbbiS will consume it, but
the core language pipeline belongs in Keprix.

| Order | Prompt |
| --- | --- |
| 47 | African language provider adapters |
| 48 | Structured intent extraction engine |
| 49 | Voice template system |
| 50 | Localization data flywheel and correction loop |

### Phase 5: Core Reference-Agent Adoption

This phase brings the first reference-agent DNA into Keprix after the foundation
can safely host it.

| Order | Prompt |
| --- | --- |
| 51 | LangGraph-style durable playbook runtime |
| 52 | CrewAI-style crews, flows, and agent teams |
| 53 | LaVague-style browser action engine |
| 54 | TaskWeaver-style data analytics code workspace |
| 55 | SWE-agent-style self-coding and patch trajectories |
| 56 | CrewAI tool library adapter pack |
| 57 | Agent evals, benchmarks, and trace observability |
| 58 | AutoGen-style multi-agent messaging and studio |
| 59 | Reference agent adoption release map |

### Phase 6: Expanded Reference-Agent DNA

This phase absorbs the additional researched agents and harmonizes them into
the same Keprix runtime, UI, trace, vault, and policy model.

| Order | Prompt |
| --- | --- |
| 60 | Reference agent gap audit and adoption matrix |
| 61 | OpenHands-style agent control center |
| 62 | Aider-style git-native coding UX |
| 63 | browser-use-style browser harness |
| 64 | smolagents-style code agent and hub tools |
| 65 | OpenAI Agents-style handoffs, guardrails, tracing, and realtime |
| 66 | Pydantic AI-style typed agents and dependency injection |
| 67 | Google ADK-style agent lifecycle and workflow app |
| 68 | Semantic Kernel-style plugin, memory, planner interoperability |
| 69 | LlamaIndex-style document agents, indexing, and RAG pipelines |
| 70 | Mastra-style TypeScript agents, workflows, memory, and evals |
| 71 | Agno-style agent platform interfaces and auto-improvement |
| 72 | Haystack-style production RAG pipelines and routing |
| 73 | Expanded reference agent adoption release map |

### Phase 7: Research Workspace and Statistical Tools

This phase turns Keprix into a serious research, evidence, and analysis workspace.

| Order | Prompt |
| --- | --- |
| 74 | Research workspace architecture and boundary |
| 75 | Obsidian vault adapter and linked notes |
| 76 | Zotero citations and Better BibTeX adapter |
| 77 | Dataset, codebook, and survey manager |
| 78 | PSPP CLI runner and SPSS syntax generator |
| 79 | jamovi export bridge and R syntax workflow |
| 80 | R, Python, and Jupyter notebook runner |
| 81 | Report generator, Pandoc, Quarto, and evidence bundles |
| 82 | Research playbooks UI and agent workflows |
| 83 | Research evals, reproducibility, and release map |

### Phase 8: Opportunity Engine

This phase lets Keprix discover opportunities, design offers, validate markets,
generate assets, and orchestrate launch workflows.

| Order | Prompt |
| --- | --- |
| 84 | Opportunity Engine architecture |
| 85 | Market demand discovery playbook |
| 86 | Pain mining playbook |
| 87 | Offer and ICP builder playbooks |
| 88 | Competitor intelligence playbook |
| 89 | Validation score playbook |
| 90 | Offer doc and agent memory playbook |
| 91 | Asset factory playbook |
| 92 | Launch orchestrator playbook |
| 93 | Growth loop playbook |
| 94 | Opportunity UI, CLI, and slash command |
| 95 | Opportunity Engine tests, docs, and release readiness |

### Phase 9: Agent Personas

Personas should be built after the runtime, orchestration, coding, research, and
opportunity layers exist, otherwise they become names without capability.

| Order | Prompt |
| --- | --- |
| 96 | NEXUS, orchestrator and project control |
| 97 | FORGE, CTO and tech lead |
| 98 | WARDEN, CISO and security lead |
| 99 | SAGE, research and intelligence |
| 100 | BEACON, marketing and client delivery |
| 101 | PRISM, SEO and organic growth |
| 102 | COMPASS, strategy and decisions |
| 103 | EMBER, wellbeing coach |
| 104 | ECHO, voice receptionist |
| 105 | CODEX, legal assistant |
| 106 | SCOUT, governance and kill switch |

### Phase 10: Safety, Regulated Workflows, and External Output

These prompts add human review, exports, GDPR controls, legal gates, and regulated
workflow boundaries.

| Order | Prompt |
| --- | --- |
| 107 | External human review gateway |
| 108 | PDF and structured document export |
| 109 | GDPR compliance infrastructure |
| 110 | Legal acceptance gate |
| 111 | Scout evidence pack and clinical event taxonomy |
| 112 | Clinical pack gate |
| 113 | Outbound notify external |

### Phase 11: Public Launch Surface

These prompts package the standalone Keprix marketing surface after the product
positioning is stable.

| Order | Prompt |
| --- | --- |
| 114 | Standalone marketing site brand and content |
| 115 | Standalone marketing site build, deploy, and analytics |

## Demonstration Gate

The build should always be tested against this core demonstration:

1. Start a fresh Keprix instance with Docker.
2. Open the web UI and CLI.
3. Connect at least one message channel and one email account.
4. Ask Keprix to perform a task it does not have a tool for.
5. Keprix detects the gap, synthesizes a tool, sandboxes it, shows the code,
   waits for approval, installs it live, and runs the task.
6. The action appears in traces, memory, audit records, and the UI.
7. A playbook can call that new tool later without a restart.

If this flow does not work, the foundation is not complete.

## Acceptance Criteria

- There is no active prompt language telling builders to postpone features to a
  later version.
- The active prompt sequence is continuous from `00` through `115`, with `00a`
  and `00b` as reference prompts.
- Prompt bodies reference the new numbers and the real implementation path:
  `/opt/lampp/htdocs/verlox/keprix/keprix/`.
- Cyber-only prompts remain archived or under Petraclus, not active Keprix core.
- Completed prompts are archived immediately after verification.
