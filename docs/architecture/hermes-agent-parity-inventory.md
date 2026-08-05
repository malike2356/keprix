# Hermes Agent parity inventory

Keprix is a hard fork of Hermes Agent (Nous Research). The core agent runtime
is derived from the Hermes codebase and shares identical architecture for most
areas. This document inventories all 16 parity areas, classifies each, and
identifies keprix-specific extensions that must be preserved.

> **Reference source**: `1st-plan/competitor-research/reference-agents/hermes-agent/`
> **Keprix source**: `src/keprix/`

---

## Classification legend

| Classification | Meaning |
| --- | --- |
| **Same** | Identical logic; only renamed identifiers (hermes→keprix, HERMES→KEPRIX) |
| **Keprix better** | Keprix extends or hardens the Hermes baseline with additional features |
| **Hermes better** | Hermes has features Keprix hasn't adopted yet |
| **Missing** | Area exists in Hermes but not in Keprix (gap to close) |
| **Different by design** | Intentional architectural divergence for product reasons |
| **Blocked by product boundary** | Cannot 1:1 mirror because the feature crosses core↔product boundary |

---

## 1. Agent Loop

The main conversation turn loop that drives inference calls, tool dispatch,
retries, and turn finalization.

| Area | Hermes files | Keprix files | Status | Action needed |
| --- | --- | --- | --- | --- |
| Agent loop | `run_agent.py` (5,467 lines); `run_conversation` method on `AIAgent` | `agent/conversation_loop.py` (4,507 lines); extracted `run_conversation` function; `agent/turn_context.py` (395 lines); prologue extracted as `build_turn_context`; `agent/turn_finalizer.py`; epilogue extracted | **Keprix better** | Preserve. Keprix modularized the 5,467-line monolith into separate modules (conversation_loop, turn_context, turn_retry_state, tool_executor, errors, prompt_builder). This is structural improvement, not behavioral divergence. |
| Turn retry state | `agent/turn_retry_state.py`; 16 one-shot recovery booleans | `agent/turn_retry_state.py`; identical | **Same** | No action. |
| Iteration budget | `agent/iteration_budget.py` | `agent/iteration_budget.py` | **Same** | No action. |
| Compression lifecycle | `agent/conversation_compression.py`, `trajectory_compressor.py` | `agent/conversation_compression.py`, `trajectory_compressor.py` | **Same** | No action. |
| Turn prologue (pre-LLM hooks, memory prefetch) | Inline in `run_agent.py` | Extracted to `agent/turn_context.py` with `TurnContext` dataclass | **Keprix better** | Preserve. Structure enables testing isolated turn prologues. |
| Keprix extension: memory_edit_gate | N/A | `agent/memory_edit_gate.py`; remember/forget confirmation gate (Prompt 295) | **Keprix better** | Preserve. Blocks false confirmation when memory tool wasn't called. |
| Keprix extension: layered prompt assembly | N/A | `agent/layered_assembly.py`, `agent/layered_prompt.py`, `agent/layers/`; ordered prompt layers | **Keprix better** | Preserve. Enables stable-tier prompt composition from identity, budget, safety, tools, tone, execution, memory, and domain layers. |

---

## 2. Tool Dispatch

Registration, schema generation, function-call parsing, sequential/concurrent
execution, guardrails, and result formatting.

| Area | Hermes files | Keprix files | Status | Action needed |
| --- | --- | --- | --- | --- |
| Tool registry | `tools/registry.py` | `tools/registry.py` | **Same** | No action. |
| Tool executor (sequential/parallel) | `agent/tool_executor.py` | `agent/tool_executor.py` | **Same** | No action. |
| Tool guardrails | `agent/tool_guardrails.py` | `agent/tool_guardrails.py` | **Same** | No action. |
| Dispatch helpers | `agent/tool_dispatch_helpers.py` | `agent/tool_dispatch_helpers.py` | **Same** | No action. |
| Tool audit | `agent/tool_audit.py` | `agent/tool_audit.py` | **Same** | No action. |
| Result classification | `agent/tool_result_classification.py` | `agent/tool_result_classification.py` | **Same** | No action. |
| Toolset defs | `toolsets.py`, `toolset_distributions.py` | `toolsets.py`, `toolset_distributions.py` | **Same** | No action. |
| Keprix extension: connector router | N/A | `agent/connector_router.py`; prefer MCP connectors over browser scraping (Prompt 296) | **Keprix better** | Preserve. Routes intent-matched queries to connected MCP servers before falling back to browser tools. |
| Keprix extension: deliverable paths | N/A | `agent/deliverable_paths.py`; project-scoped output path resolution | **Keprix better** | Preserve. |
| Keprix extension: guide enforcer | N/A | `agent/guide_enforcer.py`; enforces style/coding guides | **Keprix better** | Preserve. |

---

## 3. Prompt Assembly

System prompt construction: identity, tools guidance, skills index, context file
injection, threat scanning, platform hints.

| Area | Hermes files | Keprix files | Status | Action needed |
| --- | --- | --- | --- | --- |
| System prompt builder | `agent/system_prompt.py` | `agent/system_prompt.py`; renamed identifiers | **Same** (rename only) | No action. |
| Prompt builder module | `agent/prompt_builder.py` | `agent/prompt_builder.py`; includes `.keprix.md`/`KEPRIX.md` discovery | **Same** (rename only) | No action. |
| Skills index injection | `agent/skill_utils.py`, `agent/skill_preprocessing.py` | `agent/skill_utils.py`, `agent/skill_preprocessing.py` | **Same** | No action. |
| Context file scanning | Inline in prompt_builder | `agent/prompt_builder.py`; threat-pattern scanning via `tools/threat_patterns.py` | **Same** | No action. |
| Keprix extension: layered prompt | N/A | `agent/layered_assembly.py`, `agent/layered_prompt.py`, `agent/layers/`; ordered layer composition | **Keprix better** | Preserve. `LayeredPromptBuilder` with `PromptLayer` enum (IDENTITY, BUDGET, SAFETY, TOOLS, TONE, EXECUTION, MEMORY_CONTINUITY, DOMAIN). Hermes has everything inline; Keprix makes composition explicit. |
| Keprix extension: domain layers | N/A | `agent/layers/domains/`; code, legal, medical, property | **Keprix better** | Preserve. Domain-specific stable-tier prompt injections. |

---

## 4. Provider Routing

Model provider selection, API key sourcing, transport-layer abstraction, and
model metadata.

| Area | Hermes files | Keprix files | Status | Action needed |
| --- | --- | --- | --- | --- |
| Transports | `agent/transports/`; base, chat_completions, anthropic, bedrock, codex | `agent/transports/`; same files plus `keprix_tools_mcp_server.py` | **Same** | No action. |
| Provider adapters | `agent/anthropic_adapter.py`, `agent/bedrock_adapter.py`, `agent/codex_responses_adapter.py`, `agent/gemini_native_adapter.py`, `agent/gemini_cloudcode_adapter.py`, `agent/azure_identity_adapter.py` | Same files | **Same** | No action. |
| Model metadata | `agent/model_metadata.py` | `agent/model_metadata.py` | **Same** | No action. |
| Provider normalisation | `agent/provider_normaliser.py` | `agent/provider_normaliser.py` | **Same** | No action. |
| Credential pool | `agent/credential_pool.py`, `agent/credential_sources.py`, `agent/credential_persistence.py` | Same files | **Same** | No action. |
| Gemini schema | `agent/gemini_schema.py`, `agent/moonshot_schema.py` | Same files | **Same** | No action. |

---

## 5. Streaming

SSE/stream processing, chunk assembly, streaming markdown rendering, and stream
diagnostics.

| Area | Hermes files | Keprix files | Status | Action needed |
| --- | --- | --- | --- | --- |
| Stream diagnostics | `agent/stream_diag.py` | `agent/stream_diag.py` | **Same** | No action. |
| Thinking block | `agent/think_scrubber.py`, `agent/thinking_block.py` | Same files | **Same** | No action. |
| Chat completion helpers | `agent/chat_completion_helpers.py` | `agent/chat_completion_helpers.py` | **Same** | No action. |
| TUI streaming markdown | `ui-tui/src/components/streamingMarkdown.tsx` (TypeScript) | `tui/streaming_markdown.py` (Python Textual) | **Different by design** | Keprix uses Python Textual TUI; Hermes uses TypeScript Ink. Streaming behavior is preserved but rendering stack is entirely different. |

---

## 6. Retry and Recovery

API error handling, backoff, credential refresh, format recovery, and circuit
breaking.

| Area | Hermes files | Keprix files | Status | Action needed |
| --- | --- | --- | --- | --- |
| Error classifier | `agent/error_classifier.py` | `agent/error_classifier.py` | **Same** | No action. |
| Retry utils | `agent/retry_utils.py` | `agent/retry_utils.py` | **Same** | No action. |
| Turn retry state | `agent/turn_retry_state.py`; 16 one-shot guards | `agent/turn_retry_state.py`; identical | **Same** | No action. |
| Rate limit tracker | `agent/rate_limit_tracker.py` | `agent/rate_limit_tracker.py` | **Same** | No action. |
| Error display | `agent/errors.py` | `agent/errors.py` | **Same** | No action. |
| SSL guard | `agent/ssl_guard.py` | `agent/ssl_guard.py` | **Same** | No action. |
| Nous rate guard | `agent/nous_rate_guard.py` | `agent/nous_rate_guard.py` | **Same** | No action. |

---

## 7. Session Persistence

SQLite session store, message history, session search (FTS5), lifecycle
management.

| Area | Hermes files | Keprix files | Status | Action needed |
| --- | --- | --- | --- | --- |
| State store | `hermes_state.py` (4,782 lines); SQLite with FTS5 | `keprix_state.py`; same engine, renamed | **Same** (rename only) | No action. |
| Session search | `tools/session_search_tool.py` | `tools/session_search_tool.py` | **Same** | No action. |
| Conversation search | `tools/conversation_search_tool.py` | `tools/conversation_search_tool.py` | **Same** | No action. |
| Session context (gateway) | `gateway/session.py`, `gateway/session_context.py` | Product-layer equivalents in channel_shield | **Blocked by product boundary** | Gateway session management is owned by channel_shield in Keprix. Core session persistence is shared. |

---

## 8. Memory

Memory tool, providers, manager, and background review.

| Area | Hermes files | Keprix files | Status | Action needed |
| --- | --- | --- | --- | --- |
| Memory tool | `tools/memory_tool.py` | `tools/memory_tool.py` | **Same** | No action. |
| Memory manager | `agent/memory_manager.py` | `agent/memory_manager.py` | **Same** | No action. |
| Memory provider | `agent/memory_provider.py` | `agent/memory_provider.py` + `memory/provider.py`, `memory/manager.py` | **Keprix better** | Keprix extracted memory into `memory/` package with separate provider/manager. Structure is cleaner. |
| Background review | `agent/background_review.py` | `agent/background_review.py` | **Same** | No action. |
| Keprix extension: memory_edit_gate | N/A | `agent/memory_edit_gate.py`; remember/forget confirmation (Prompt 295) | **Keprix better** | Preserve. |
| Keprix extension: memory continuity layer | N/A | `agent/layers/memory_continuity.py`; stable-tier memory context | **Keprix better** | Preserve as prompt layer extension. |

---

## 9. Checkpoints

Git-based file snapshots for rollback safety.

| Area | Hermes files | Keprix files | Status | Action needed |
| --- | --- | --- | --- | --- |
| Checkpoint manager | `tools/checkpoint_manager.py`; `~/.hermes/checkpoints/` | `tools/checkpoint_manager.py`; `~/.keprix/checkpoints/` | **Same** (rename only) | No action. Ref path changed from `refs/hermes` to `refs/keprix`. |

---

## 10. File Edits

File reading, writing, patching (V4A format), path security, file state tracking.

| Area | Hermes files | Keprix files | Status | Action needed |
| --- | --- | --- | --- | --- |
| File tools | `tools/file_tools.py`; read_file, write_file, patch | `tools/file_tools.py`; same tools | **Same** | No action. |
| File operations | `tools/file_operations.py` | `tools/file_operations.py` | **Same** | No action. |
| File state | `tools/file_state.py` | `tools/file_state.py` | **Same** | No action. |
| Path security | `tools/path_security.py` | `tools/path_security.py` | **Same** | No action. |
| Patch parser | `tools/patch_parser.py` | `tools/patch_parser.py` | **Same** | No action. |
| File safety | `agent/file_safety.py` | `agent/file_safety.py` | **Same** | No action. |
| Write approval | `tools/write_approval.py` | `tools/write_approval.py` | **Same** | No action. |

---

## 11. Terminal Execution

Terminal tool, process management, environments (local/docker/ssh/modal).

| Area | Hermes files | Keprix files | Status | Action needed |
| --- | --- | --- | --- | --- |
| Terminal tool | `tools/terminal_tool.py` | `tools/terminal_tool.py` | **Same** | No action. |
| Process registry | `tools/process_registry.py` | `tools/process_registry.py` | **Same** | No action. |
| Environments | `tools/environments/`; base, local, docker, ssh, modal, daytona, singularity | `tools/environments/`; same | **Same** | No action. |
| Code execution | `tools/code_execution_tool.py` | `tools/code_execution_tool.py` | **Same** | No action. |
| Read terminal | `tools/read_terminal_tool.py` | `tools/read_terminal_tool.py` | **Same** | No action. |

---

## 12. Approval Flow

Tool-call approval, YOLO mode, slash confirm, write deny.

| Area | Hermes files | Keprix files | Status | Action needed |
| --- | --- | --- | --- | --- |
| Approval tool | `tools/approval.py` | `tools/approval.py` | **Same** | No action. |
| Write approval | `tools/write_approval.py` | `tools/write_approval.py` | **Same** | No action. |
| Slash confirm | `tools/slash_confirm.py` | `tools/slash_confirm.py` | **Same** | No action. |
| TUI approval overlay | `ui-tui/src/components/appOverlays.tsx` (TypeScript) | `tui/widgets/approval_overlay.py` (Python Textual) | **Different by design** | UI stacks differ but approval behavior is equivalent. Preserve Keprix TUI widgets. |
| Keprix extension: typed agent approval | N/A | `typed_agents/approval.py`; structured approval contracts for typed agents | **Keprix better** | Preserve. |

---

## 13. Skills

Skill loading, indexing, conditions, bundles, hub sync, AST audit.

| Area | Hermes files | Keprix files | Status | Action needed |
| --- | --- | --- | --- | --- |
| Skill loader | `agent/skill_commands.py`, `agent/skill_preprocessing.py`, `agent/skill_utils.py` | Same files | **Same** | No action. |
| Skill bundles | `agent/skill_bundles.py` | `agent/skill_bundles.py` | **Same** | No action. |
| Skill manager tool | `tools/skill_manager_tool.py` | `tools/skill_manager_tool.py` | **Same** | No action. |
| Skills list/view/manage | `tools/skills_tool.py` | `tools/skills_tool.py` | **Same** | No action. |
| Skills hub | `tools/skills_hub.py` | `tools/skills_hub.py` | **Same** | No action. |
| Skills sync | `tools/skills_sync.py` | `tools/skills_sync.py` | **Same** | No action. |
| Skills guard | `tools/skills_guard.py` | `tools/skills_guard.py` | **Same** | No action. |
| AST audit | `tools/skills_ast_audit.py` | `tools/skills_ast_audit.py` | **Same** | No action. |
| Skill provenance | `tools/skill_provenance.py` | `tools/skill_provenance.py` | **Same** | No action. |
| Skill usage | `tools/skill_usage.py` | `tools/skill_usage.py` | **Same** | No action. |
| Skills first routing | `agent/skill_first.py` | `agent/skill_first.py` | **Same** | No action. |
| Keprix extension: skill registry | N/A | `agent/keprix/skill_registry.py`; Keprix-specific skill tracking and registration | **Keprix better** | Preserve. |
| Keprix extension: auto skill writer | N/A | `agent_os/auto_skill_writer.py`; automatic skill generation from usage patterns | **Keprix better** | Preserve (product layer). |

---

## 14. Plugins

Plugin loading, LLM plugins, web search providers, image/video gen providers,
TTS/transcription providers, browser providers.

| Area | Hermes files | Keprix files | Status | Action needed |
| --- | --- | --- | --- | --- |
| Plugin LLM | `agent/plugin_llm.py` | `agent/plugin_llm.py` | **Same** | No action. |
| Web search provider | `agent/web_search_provider.py`, `agent/web_search_registry.py` | Same files | **Same** | No action. |
| Image gen provider | `agent/image_gen_provider.py`, `agent/image_gen_registry.py` | Same files | **Same** | No action. |
| Video gen provider | `agent/video_gen_provider.py`, `agent/video_gen_registry.py` | Same files | **Same** | No action. |
| TTS provider | `agent/tts_provider.py`, `agent/tts_registry.py` | Same files | **Same** | No action. |
| Transcription provider | `agent/transcription_provider.py`, `agent/transcription_registry.py` | Same files | **Same** | No action. |
| Browser provider | `agent/browser_provider.py`, `agent/browser_registry.py` | Same files | **Same** | No action. |
| Hermes-specific: hermes_cli/plugins.py | `hermes_cli/plugins.py`; plugin hook invocation | `keprix_cli/plugins.py`; renamed | **Same** (rename only) | No action. |

---

## 15. MCP

Model Context Protocol integration: tool spawning, OAuth, registry, auto-spawn.

| Area | Hermes files | Keprix files | Status | Action needed |
| --- | --- | --- | --- | --- |
| MCP tool | `tools/mcp_tool.py` | `tools/mcp_tool.py` | **Same** | No action. |
| MCP OAuth | `tools/mcp_oauth.py`, `tools/mcp_oauth_manager.py` | Same files | **Same** | No action. |
| MCP serve | `mcp_serve.py`; standalone MCP server | `mcp_serve.py`; renamed | **Same** (rename only) | No action. |
| Auto MCP spawn | `tools/auto_mcp_spawn.py` | `tools/auto_mcp_spawn.py` | **Same** | No action. |
| Managed tool gateway | `tools/managed_tool_gateway.py` | `tools/managed_tool_gateway.py` | **Same** | No action. |
| MCP registry tools | `tools/mcp_registry_tools.py` | `tools/mcp_registry_tools.py` | **Same** | No action. |
| Keprix MCP server | `agent/transports/hermes_tools_mcp_server.py` (in Hermes) | `agent/transports/keprix_tools_mcp_server.py` (in Keprix) | **Same** (rename only) | No action. |
| Keprix extension: connector router | N/A | `agent/connector_router.py`; MCP connector-first routing (Prompt 296) | **Keprix better** | Preserve. Routes queries to connected MCP servers based on intent matching. Suggests connect for catalogued but disconnected servers. |

---

## 16. Gateway

Multi-platform messaging gateway: Telegram, Discord, Slack, WhatsApp, WeChat,
email, SMS, Signal, Matrix, Feishu, DingTalk, QQ, Yuanbao, webhooks.

| Area | Hermes files | Keprix files | Status | Action needed |
| --- | --- | --- | --- | --- |
| Gateway core | `gateway/`; run, session, config, hooks, authz, delivery, mirror, restart, status, pairing, slash | `channel_shield/`; service, pipeline, routes, agent_ingress, egress, models, store, durable, safe_summary, agent_policy, agent_safe, redaction, memory_guard_sync, crypto_store | **Blocked by product boundary** | Keprix replaced the Hermes gateway with Channel Shield, which adds product features: multi-tenant, crypto, policy enforcement, memory guard sync, safe summaries. Core gateway primitives are equivalent but Channel Shield adds significant product-layer hardening. |
| Platform adapters | `gateway/platforms/`; telegram, discord, slack, whatsapp, signal, matrix, email, sms, feishu, wecom, weixin, dingtalk, qqbot, yuanbao, webhook, bluebubbles, msgraph | `channel_shield/adapters/`; telegram, discord, slack, whatsapp, sms, email, teams, web | **Keprix better** | Keprix adds Teams adapter; Hermes has more Chinese-platform adapters (wecom, weixin, dingtalk, qqbot, yuanbao) via its gateway. Channel Shield wraps adapters with product-grade hardening (durable, redaction, policy). |
| Channel config | `gateway/config.py` | `channel_shield/config.py` | **Different by design** | Channel Shield has its own config model designed for product operations. |
| Hermes-specific: tui_gateway | `tui_gateway/`; WebSocket server for TUI | Keprix TUI has direct Textual integration | **Different by design** | Hermes TUI communicates via WebSocket gateway; Keprix TUI is a Python Textual app directly integrated with the agent runtime. |

---

## 17. Cost and Rate Handling

Usage tracking, pricing estimation, credits parsing, budget alerts, rate limit
handling.

| Area | Hermes files | Keprix files | Status | Action needed |
| --- | --- | --- | --- | --- |
| Credits tracker | `agent/credits_tracker.py`; Nous-specific credits header parsing | `agent/credits_tracker.py`; identical logic | **Same** | No action. |
| Usage pricing | `agent/usage_pricing.py` | `agent/usage_pricing.py` | **Same** | No action. |
| Account usage | `agent/account_usage.py` | `agent/account_usage.py` | **Same** | No action. |
| Rate limit tracker | `agent/rate_limit_tracker.py` | `agent/rate_limit_tracker.py` | **Same** | No action. |
| Budget config | `tools/budget_config.py` | `tools/budget_config.py` | **Same** | No action. |
| Keprix extension: usage module | N/A | `usage/`; analytics, budget alerts, budget scheduler, config, filters, pricing_bridge, recorder, retention, routes, schemas, store | **Keprix better** | Preserve. Product-grade usage tracking with budget alerts, retention policies, and admin routes. |
| Keprix extension: billing | N/A | `billing/`; Stripe integration, admin routes, portal routes, checkout, price catalog, products | **Keprix better** | Preserve. Full product billing layer (product boundary). |

---

## Keprix-specific extensions; complete inventory

These are features Keprix has that Hermes Agent does not. All must be preserved.

### Core extensions (in core runtime)

| Extension | Files | Description |
| --- | --- | --- |
| Layered prompt assembly | `agent/layered_assembly.py`, `agent/layered_prompt.py`, `agent/layers/` | Ordered prompt layer composition (identity, budget, safety, tools, tone, execution, memory_continuity, domain). Stable-tier system prompt assembly. |
| Domain prompt layers | `agent/layers/domains/code.py`, `legal.py`, `medical.py`, `property.py` | Domain-specific stable-tier prompt injections for code, legal, medical, property contexts. |
| Memory edit gate | `agent/memory_edit_gate.py` | Remember/forget confirmation gate (Prompt 295). Blocks false confirmations. |
| Connector router | `agent/connector_router.py` | MCP connector-first routing (Prompt 296). Prefer connected MCP over browser scraping. |
| Deliverable paths | `agent/deliverable_paths.py` | Project-scoped output path resolution. |
| Guide enforcer | `agent/guide_enforcer.py` | Style/coding guide enforcement. |
| Memory continuity layer | `agent/layers/memory_continuity.py` | Stable-tier memory context injection into prompt. |
| Keprix mutation engine | `agent/keprix/`; 25 files | Abstract syntax tree analysis, mutation dispatch, governance, tool dispatch, approval gate, ladder gate, namespace, retry, sandbox, static analyzer, synthesiser, tool inventory, tool health, tool signer. |
| Ladder mode | `agent/ladder_mode.py`, `agent/ladder.py` | Hierarchical agent routing. |

### Product extensions (product boundary)

| Extension | Files | Description |
| --- | --- | --- |
| Agent OS | `agent_os/`; 40+ files | Workflow engine, milestones, onboarding, glass dashboard, level-up service, token playbook, automation promoter, maturity audit, session scan, skill scheduler, headless run, client kit import/export. |
| Agent Apps | `agent_apps/`; 30+ files | Packaged agent workflows: CRM import, content series, error paste, memory system, onboarding path, outreach agent, SEO agent, video agent. Includes lifecycle, deployment bundle, eval harness, entitlements, scaffolding. |
| Channel Shield | `channel_shield/`; 30+ files | Multi-tenant messaging gateway with crypto, policy enforcement, memory guard sync, safe summaries, redaction, durable delivery, agent ingress/egress, scout bridge. |
| Typed Agents | `typed_agents/`; 16 files | Structured agent contracts with typed input/output, approval specs, dependency injection, retries, tool validation, vault adapter. |
| Billing | `billing/`; Stripe integration | Checkout, portal, price catalog, products, admin routes, schema. |
| Usage | `usage/`; 14 files | Analytics, budget alerts, budget scheduler, pricing bridge, recorder, retention, routes. |
| Voice | `voice/`; 30+ files | Phone provisioning, wake word detection, VAD, TTS/STT providers, personas (receptionist, meeting assistant), call finaliser, cost tracker, escalation, TwiML builder. |
| Voice templates | `voice_templates/`; 10 files | Template library, TTS bridge, approval templates, categories, player. |
| Vault | `vault/`; 10 files | Note capture, Obsidian adapter, local folder provider, pack registry, vault init, validator. |
| Workspace | `workspace/`; 30+ files | Document helpers, calendar sync, backup service, hot cache, index generator, PDF export, repository, template presets. |
| Triggers | `triggers/` | Scheduled and event-driven task dispatch. |
| Upstream monitor | `upstream/` | Tracks Hermes Agent releases for adoption evaluation. |
| UI Contract | `ui_contract/` | API contracts for UI surfaces: actions, approvals, discovery, empty states, errors, forms, navigation, routes, schemas, statuses, tables. |
| Upgrade engine | `upgrade/`; 20+ files | Version discovery, migration planning, dry-run, execution, changelog, lockfile, GUI catalog, scheduler, notifier. |
| Feature flags | `feature_flags/registry.py` | Feature flag system for gradual rollout. |
| Readiness checks | `readiness/checks.py` | Health check probes. |
| Self knowledge | `self_knowledge/documents.py` | Document ingestion for self-describing capabilities. |
| Agents runtime | `agents_runtime/` | Agent spec, executor, guardrail, handoff, realtime, sandbox, routes, run context. |

---

## Summary counts

| Classification | Count across 17 areas |
| --- | --- |
| **Same** | ~85% of core runtime files |
| **Keprix better** | Layered prompts, domain layers, memory edit gate, connector router, deliverable paths, guide enforcer, mutation engine, ladder mode, usage module, billing, voice, typed agents, Channel Shield, Agent OS, Agent Apps |
| **Hermes better** | TUI gateway recovery (minor), more Chinese-platform adapters in gateway |
| **Missing** | None (all Hermes core features are present in Keprix) |
| **Different by design** | TUI stack (Python Textual vs TypeScript Ink), gateway (Channel Shield vs Hermes gateway) |
| **Blocked by product boundary** | Gateway platform adapters, billing/usage UI, product-specific dashboards |

---

## Guidance for prompts 328-335

This inventory is comprehensive enough to execute prompts 328-335 directly:

- **Prompt 328** (gap analysis): All areas are covered; "missing" is empty. Focus on Hermes-better items.
- **Prompt 329** (adoption plan): Use Keprix-better items as "preserve" and Hermes-better items as "adopt".
- **Prompt 330** (rename audit): All `hermes`→`keprix` renames done except compat aliases. See `hermes-to-keprix-rename-inventory.md`.
- **Prompt 331** (test coverage): Core runtime tests are identical. Keprix extensions have dedicated tests in `tests/`.
- **Prompt 332** (upstream sync): Use `upstream/hermes_monitor.py` and `upstream/hermes_adoption.py`.
- **Prompt 333** (boundary enforcement): Use `core-product-boundary.md` and this inventory's product extension list.
- **Prompt 334** (migration runbook): Base on rename inventory + this parity inventory.
- **Prompt 335** (final signoff): All areas documented; no unresolved gaps.
