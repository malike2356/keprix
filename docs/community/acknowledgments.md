# Acknowledgments

## How Keprix was built

Keprix is an original AI agent operating system. It is also the product of deliberate research into how the best agent frameworks in the open-source ecosystem solve hard problems.

Before writing the bulk of Keprix's code, the team studied 21 open-source agent platforms in depth: reading source, running them locally, auditing their architecture, and understanding the trade-offs each one made. That research shaped every major design decision in Keprix.

This page records what was studied, what was learned, and where Keprix drew the line between research and inheritance. It exists because intellectual honesty is good practice, and because the authors of these projects deserve direct acknowledgment.

---

## Hermes Agent: the CLI ancestor

Keprix's CLI runtime is derived directly from **Hermes Agent**, published by Nous Research under the MIT licence. The codebase was forked, renamed from `hermes` to `keprix`, and substantially extended.

The Nous Research copyright is preserved in
[THIRD_PARTY_NOTICES.md](https://github.com/malike2356/keprix/blob/main/THIRD_PARTY_NOTICES.md)
at the project root, as the MIT licence requires.

| | |
|---|---|
| Upstream | [Hermes Agent](https://github.com/nousresearch/hermes-agent) by Nous Research |
| Licence | MIT, Copyright (c) 2025 Nous Research |
| What was taken | CLI runtime: the interactive REPL, toolset dispatch, bootstrap layer, skill loader, and terminal interface |
| What Keprix added above it | Workspace OS, multi-tenancy, operator dashboard, Aiva/Carina integration, Scout governance, vault, playbooks, agent teams, and the full feature set described in this documentation |

---

## Research foundations: 20 frameworks

The 20 projects below did not contribute source code to Keprix. Each was studied to understand how it approached a specific class of problem. In each case Keprix designed its own solution, informed by what the research revealed.

No source code from any of these projects is present in the Keprix codebase. Each project retains its own licence and identity.

| Project | What Keprix studied | How Keprix approaches it | Licence |
|---|---|---|---|
| [OpenClaw](https://github.com/openclaw/openclaw) | Channel gateway architecture; mobile client patterns; CLI-to-web session bridging | Keprix redesigned the channel layer around its own workspace session model and operator permission system, unifying web, mobile, Telegram, and Discord behind one gateway | MIT |
| [Odysseus](https://github.com/odysseus-ai/odysseus) | Research workspace design; SearXNG integration; deep research pipeline orchestration | Keprix's Deep Research is an independent implementation using its own 4-stage pipeline (Plan, Retrieve, Synthesise, Report) with configurable depth and Zotero/Obsidian export | Apache 2.0 |
| [LangGraph](https://github.com/langchain-ai/langgraph) | Durable execution graphs; checkpoint and resume; interrupt handling for long-running agent tasks | Keprix built its own playbook runtime with YAML-defined step graphs, native approval gates, vault secret resolution, and Scout governance events rather than adopting LangGraph as a runtime dependency | MIT |
| [CrewAI](https://github.com/crewAIInc/crewAI) | Role-based agent crews; YAML flow definitions; task delegation between specialist agents | Keprix's Agent Teams compile YAML crew definitions into its own playbook graph format, integrating with the same approval and trace system used by all other automations | MIT |
| [AutoGen](https://github.com/microsoft/autogen) | Group chat messaging patterns for multi-agent coordination; speaker selection; conversation memory | Keprix's persona messaging adopts a similar conversation-first model but runs entirely inside the Keprix workspace with shared vault, audit log, and feature gate integration | MIT |
| [LaVague](https://github.com/lavague-ai/LaVague) | Browser action engine design; DOM-grounded instruction execution; natural language to browser action | Keprix's browser engine is an independent implementation with governed skill definitions, dry-run harness, credentialed session isolation, and operator-level approval gates per skill | Apache 2.0 |
| [browser-use](https://github.com/browser-use/browser-use) | Browser automation architecture; DOM action planning; handling authenticated web workflows | Informed the same browser engine design as LaVague; Keprix synthesised both into one implementation | MIT |
| [TaskWeaver](https://github.com/microsoft/TaskWeaver) | Verified Python analytics session design; code generation with artifact capture; planner and executor separation | Keprix's analytics workspace runs a sandboxed Python interpreter with the same code-transparency principle but integrates output directly into workspace artifacts and playbook runs | MIT |
| [SWE-agent](https://github.com/princeton-nlp/SWE-agent) | Software engineering agent loop design; patch trajectory format; test-and-repair cycles | Keprix's self-coding agent draws on the patch loop concept but adds repo map awareness, operator commit approval, and a governed workspace scope that prevents the agent from acting outside its assigned project | MIT |
| [OpenHands](https://github.com/All-Hands-AI/OpenHands) | Self-hostable software engineering agent architecture; runtime sandboxing; workspace-level agency | Keprix studied the full self-hosted runtime model; its own coding workspace combines patch generation, test gating, and commit approval inside the operator dashboard | MIT |
| [Aider](https://github.com/Aider-AI/aider) | Git-native coding UX; repo map generation; disciplined patch application; architect and editor model split | Keprix's self-coding agent uses a similar repo-map-first approach but keeps every commit behind an operator approval step and logs all changes to the workspace audit trail | Apache 2.0 |
| [smolagents](https://github.com/huggingface/smolagents) | Minimal code-agent patterns; compact tool execution loop; code-as-action philosophy | Keprix's tool dispatch is more structured than smolagents' minimal approach but drew from it to keep the tool invocation surface clean and auditable | Apache 2.0 |
| [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) | Agent app manifest format; handoffs between agents; guardrails; structured tool calling; built-in tracing | Keprix's Agent Studio manifest format and runner are independent designs that solve the same problem; the SDK's tracing approach informed Keprix's own OTLP-compatible trace system | MIT |
| [Pydantic AI](https://github.com/pydantic/pydantic-ai) | Typed production agent design; schema-first tool definitions; validated structured output | Keprix's typed agent manifests use Pydantic models internally for validation but are implemented independently with Keprix's own lifecycle and approval model | MIT |
| [Google ADK](https://github.com/google/adk-python) | Agent lifecycle management; tool and sub-agent composition; eval suite design; deployment patterns | Keprix studied ADK's agent folder structure and eval patterns; its own eval system uses configurable grader types and OTLP export rather than ADK's runner | Apache 2.0 |
| [Semantic Kernel](https://github.com/microsoft/semantic-kernel) | Enterprise plugin architecture; memory abstractions; planner design for multi-step reasoning | Keprix's skill and plugin system draws on the plugin contract concept but replaces the planner with its own playbook runtime and integrates plugins through the unified tool registry | MIT |
| [LlamaIndex](https://github.com/run-llama/llama_index) | Data-heavy RAG design; document indexing strategies; retrieval workflow orchestration | Keprix's RAG pipeline module is an independent implementation supporting multiple index backends (ChromaDB, Qdrant, Weaviate, pgvector) with a source connector model and scheduling | MIT |
| [Mastra](https://github.com/mastra-ai/mastra) | TypeScript-native agent and workflow design; memory integration; eval framework for TypeScript stacks | Keprix studied Mastra's TypeScript-first approach when designing the SDK workflow compiler that lets TypeScript callers define playbook graphs outside the YAML format | MIT |
| [Agno](https://github.com/agno-agi/agno) | Lightweight multi-agent app building; fast tool orchestration; minimal framework surface area | Keprix's persona improvement loop draws on Agno's lightweight composition model; the two differ primarily in that Keprix ties everything to a persistent workspace with memory and governance | Apache 2.0 |
| [Haystack](https://github.com/deepset-ai/haystack) | Production RAG pipeline architecture; pipeline evaluation patterns; component-based data processing | Keprix's RAG pipeline evaluation draws from Haystack's evaluation approach; the pipeline execution itself is Keprix's own implementation integrated with the workspace artifact store | Apache 2.0 |

---

## What Keprix adds

The table above covers where Keprix drew from existing work. The following are Keprix-original:

- The workspace OS: multi-tenancy, operator workspaces, user isolation, and the full workspace shell
- The opportunity engine and growth loop
- The COMPASS persona system and mutation engine
- The Scout governance bridge and commercial tier gate model
- The Aiva and Carina integration layer
- The operator dashboard, feature flags, and control center
- The combined synthesis: one self-hosted system that unifies agent runtime, workspace tools, developer platform, messaging channels, and governance under a single operator-controlled deployment

None of the 21 projects above ship this combination. Keprix's contribution is the integration layer and the product design choices that make it deployable, governable, and extendable as a platform.

---

## Licence summary

Keprix (Community Edition) is published under the MIT licence. See
[LICENSE](https://github.com/malike2356/keprix/blob/main/LICENSE).

For incorporated code (Hermes Agent), the upstream copyright is preserved in
[THIRD_PARTY_NOTICES.md](https://github.com/malike2356/keprix/blob/main/THIRD_PARTY_NOTICES.md).

For the 20 research-only frameworks: no licence obligation applies, but this page exists because transparency about research foundations is the right practice in open-source software development.
