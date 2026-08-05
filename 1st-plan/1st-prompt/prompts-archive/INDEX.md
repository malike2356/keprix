# Completed Keprix Build Prompts

Prompts moved here after implementation was verified in the repo.

## Archive rule

Move a prompt here only when:

- The requested modules, routes, tests, and docs exist in `src/keprix/` (or documented equivalents).
- Automated tests for the prompt pass (or manual checks are documented if no harness exists).
- The prompt is no longer the active execution target for new work.

Do not delete archived prompts. Other prompts may still reference them as dependencies.

**Do not archive** prompts whose implementation lives only under `keprix/keprix/backend/` without routes on `src/keprix/api/server.py`. Prompts 52, 53, 54, and 56 were returned to `pending-prompts/` for this reason (2026-07-05).

## Completed prompts

| Prompt | Title | Implementation summary |
| --- | --- | --- |
| 01 | Developer identity and local access | `src/keprix/keys/`, `keprix init`, `keprix identity status|revoke`, `docs/developer-identity.md`, `tests/keys/` |
| 02 | Security foundation and platform hardening | `src/keprix/security/`, `src/keprix/api/server.py`, `scripts/audit-deps.sh`, `tests/security/`, Alembic `001_audit_log` |
| 06 | Memory and RAG | `src/keprix/memory/`, episodic store, RAG indexer/retriever, `/api/memory/*`, `/api/rag/*`, `tests/memory/` |
| 08 | Vault credentials and secrets | `src/keprix/security/vault_routes.py`, `vault_store`, `vault_session`, `/api/vault/*`, `tests/security/test_vault_api.py`, `tests/security/test_backup_api.py` |
| 09 | Agent-managed credential setup | `src/keprix/setup/`, `/api/setup/*`, `tests/setup/test_setup_api.py` |
| 10 | Workspace documents, notes, tasks, calendar | `src/keprix/workspace/`, `/api/workspace/*`, `tests/workspace/`, frontend `workspace-api.ts` |
| 11 | Email integration | `src/keprix/email/`, `/api/email/*`, MCP server, `tests/email/` |
| 12 | Contact manager and sync | `src/keprix/contacts/`, `/api/contacts/*`, import VCF/CSV, `tests/contacts/` |
| 14 | Deep research and playbook | `src/keprix/research/`, `src/keprix/playbook/` (local models), `src/keprix/compare/`, frontend pages, `tests/research/`, `tests/playbook/test_playbook_api.py`, `tests/compare/`, Alembic `002_research_playbook_compare` |
| 16 | Self-configuration | `src/keprix/config/` (health, auto-repair, optimizer, env discovery), `src/keprix/agents/self_config_agent.py`, `keprix_cli/self_config_commands.py`, `tests/config/` |
| 33 | Installer and zero-to-running | `src/keprix/installer/`, `scripts/install.sh`, `scripts/wizard.py`, `scripts/update.sh`, `keprix setup-wizard|health|update|backup`, `tests/installer/` |
| 48 | Structured intent extraction engine | `backend/intent/`, `/api/intent/*`, `skill_loader`, borehole domain intents, language middleware hook, `tests/intent/` |
| 20 | App Foundation SDK | `src/keprix/sdk/`, `keprix_sdk/python/`, `keprix_sdk/typescript/`, `/api/sdk/*`, `keprix sdk`, `tests/sdk/` |
| 23 | Slash commands | `src/keprix/slash/`, `src/keprix/gateway/slash/`, `/api/slash/*`, `keprix slash`, `tests/slash/` |
| 26 | Agent hardening | `src/keprix/agent/keprix/` (AST, seccomp, approval gate, signer, health, namespace), `tests/mutation/test_hardening.py` |
| 28 | Keprix self-coding / mutation engine | `src/keprix/agent/keprix/` (gap detector, synthesiser, sandbox, approval, installer), `/api/agent/tools/generated/*`, `tests/mutation/` |
| 51 | LangGraph-style durable playbook runtime | `src/keprix/playbook/runtime/`, `src/keprix/playbook/run_routes.py`, `tests/playbook/test_runtime_*.py`, `tests/playbook/test_playbook_run_api.py` |
| 55 | SWE-agent patch trajectories | `src/keprix/coding/`, `/api/coding/*`, `keprix coding`, `tests/coding/` |
| 62 | Aider-style git-native coding UX | extends `src/keprix/coding/` (repo map, git workflow, lint/test loop, watch mode, context loader), frontend coding panels, `tests/coding/` |
| 64 | Smolagents code agent and hub tools | `src/keprix/code_agent/`, `src/keprix/hub/`, `/api/code-agent/*`, `tests/code_agent/`, `tests/hub/` |
| 71 | Agno-style interfaces and auto-improvement | `src/keprix/interfaces/`, `src/keprix/improvement/`, `/api/interfaces/*`, `/api/improvement/*`, `tests/interfaces/`, `tests/improvement/` |
| 84 | Opportunity Engine architecture | `src/keprix/opportunity/`, `/api/opportunities/*`, `keprix opportunity`, `feature_flags.opportunity_engine`, `tests/opportunity/` |
| 85 | Market demand discovery playbook | `playbooks/market_demand.py`, `templates/market-demand-*`, `01-market-demand.md`, `tests/opportunity/test_market_demand.py` |
| 86 | Pain mining playbook | `playbooks/pain_mining.py`, `02-pain-mining.md`, citation/sanitisation tests |
| 87 | Offer and ICP builder playbooks | `offer_builder.py`, `icp_builder.py`, `03-offer.md`, `03-icp.md`, dedicated tests |
| 88 | Competitor intelligence playbook | `competitor_intelligence.py`, `04-competitors.md`, `tests/opportunity/test_competitor_intelligence.py` |
| 89 | Validation score playbook | `validation_score.py`, `12-validation-score.md`, threshold-65 gate, `tests/opportunity/test_validation_score.py` |
| 75 | Obsidian vault adapter | `research_workspace/obsidian/`, routes, backlinks/graph export, `tests/research_workspace/test_obsidian_*.py` |
| 90 | Offer doc and agent memory playbook | `src/keprix/opportunity/playbooks/offer_doc_generator.py`, `templates/canonical-offer-doc.md`, `templates/agent-memory-brief.md`, `load_canonical_offer_doc()`, episodic memory tags, `tests/opportunity/test_offer_doc_generator.py` |
| 91 | Asset factory playbook | `src/keprix/opportunity/playbooks/asset_factory.py`, `templates/asset-factory-system.md`, `assets/` subfolder writers, claim validation, `tests/opportunity/test_asset_factory.py` |
| 92 | Launch orchestrator playbook | `src/keprix/opportunity/playbooks/launch_orchestrator.py`, `integrations.py`, `run_launch_plan(dry_run=True)`, approval gates, `tests/opportunity/test_launch_orchestrator.py` |
| 93 | Growth loop playbook | `src/keprix/opportunity/playbooks/growth_loop.py`, `templates/growth-loop-report.md`, ranked experiments, manual import fallback, `tests/opportunity/test_growth_loop.py` |
| 94 | Opportunity UI, CLI, slash command | `frontend/src/app/(workspace)/opportunities/`, `frontend/src/lib/opportunity-api.ts`, `keprix opportunity`, `/opportunity` slash, `tests/frontend/test_opportunity_surfaces.py` |
| 95 | Opportunity Engine tests, docs, release | `tests/fixtures/opportunity/`, `tests/opportunity/test_opportunity_release.py`, `docs/opportunity-engine*.md`, weak-demand validation gate, 105 opportunity tests |
| 136 | Agent conversation workspace | `src/keprix/api/conversation_routes.py`, `frontend/src/app/(workspace)/chat/`, `frontend/src/components/workspace/`, `tests/api/test_conversations.py` |
| 139 | Chat mutation bridge and tool inventory | `src/keprix/agent/keprix/chat_mutation_bridge.py`, `tool_inventory.py`, `_stream_assistant_reply` wiring, `tests/api/test_chat_mutation_stream.py`, `tests/mutation/test_tool_inventory.py` |
| 140 | Gap detector LLM and demo patterns | `src/keprix/agent/keprix/gap_detector.py`, `gap_classifier_prompt.py`, `track_time` fast path, LLM `classify_async`, synthesiser fallback, `tests/mutation/test_gap_detector.py` |
| 141 | Mutation approve retry and chat follow-up | `src/keprix/agent/keprix/retry.py`, `approval.py`, approve API `retry_message` + session message persist, `MutationCard`/`useChat`, `tests/api/test_mutation_approve_retry.py`, `tests/mutation/test_retry.py` |
| 142 | Gateway WEB_UI NDJSON stream bridge | `src/keprix/interfaces/web_ui_stream.py`, `web_ui_stream_events.py`, `interface_registry.dispatch_stream`, `KEPRIX_CHAT_GATEWAY_STREAM`, `tests/interfaces/test_web_ui_stream.py`, extended `tests/api/test_conversation_routing.py` |
| 143 | Agent loop mutation hook on tool miss | `src/keprix/agent/keprix/tool_dispatch.py`, `mutation_hook.py`, `governance.py`, `KEPRIX_CHAT_MUTATION_SIDECAR`, `tests/mutation/test_agent_loop_mutation.py` |
| 145 | LLM usage persistence and instrumentation | `src/keprix/usage/`, migration 014, recorder at LLM call sites, `tests/usage/test_store.py`, `test_recorder.py` |
| 146 | LLM usage analytics API | `/api/usage/*`, budget store (migration 015), `keprix usage` CLI, `docs/features/llm-usage.md`, `tests/usage/test_analytics_api.py` |
| 147 | LLM usage workspace dashboard | `frontend/src/app/(workspace)/usage/`, `usage-api.ts`, `components/usage/`, nav, `tests/frontend/test_usage_dashboard.py` |
| 148 | Admin LLM usage and budgets | `/dashboard/usage`, overview stat card, budget alerts, `budget_alert_scheduler.py`, `tests/usage/test_admin_usage.py`, `tests/frontend/test_admin_usage_dashboard.py` |
| 137 | Admin workspace pages | `src/keprix/api/admin_workspace_routes.py`, `frontend/src/app/(admin)/dashboard/`, `frontend/src/components/admin/`, `tests/api/test_admin_workspace.py` |
| 116 | UI foundation, theme, and setup | `frontend/src/theme/`, `components/cards/`, `components/shared/`, `(marketing)/`, `(admin)/`, `(workspace)/`, auth routes |
| 117 | Marketing landing page | `frontend/src/app/(marketing)/`, `components/marketing/`, `/` hero tagline, `/legal/*`, `/docs` |
| 118 | Admin dashboard with Flexy | `frontend/src/app/(admin)/dashboard/`, Tabler icons, Flexy shell, overview charts, 9 admin pages |
| 18 | API surface and observability | `src/keprix/api/server.py`, `src/keprix/observability/`, `src/keprix/api/public_v1_routes.py`, `tests/api/test_observability.py`, `tests/cli/test_observability_cli.py` |
| 21 | Frontend UI and launchers | `frontend/src/app/(workspace)/`, `frontend/src/lib/ce-api.ts`, `frontend/src/lib/ce-auth.tsx`, `tests/frontend/test_prompt21_guards.py` |
| 22 | Unified UI/UX design system and app shell | `ui/design-system/`, `src/keprix/ui_contract/`, `frontend/src/components/shell/`, `tests/ui/`, `tests/frontend/test_prompt22_guards.py` |
| 107 | External human review gateway | `src/keprix/review_gateway/`, public `/review/{token}`, operator UI, `tests/review_gateway/` |
| 108 | PDF export persistence | `src/keprix/export/`, `ExportStore`, `GET /api/export/{file_id}`, agent tool, `tests/export/` |
| 109 | GDPR privacy centre | `src/keprix/privacy/`, retention policy API + UI, dry-run erasure, `tests/privacy/` |
| 110 | Legal acceptance gate | `src/keprix/legal/`, 451 middleware, `/legal/accept`, GDPR consent hook, `tests/legal/` |
| 111 | Scout evidence pack and clinical taxonomy | `src/keprix/scout/clinical_events.py`, `clinical_store.py`, `evidence_pack/`, `/api/evidence-pack/*`, governance UI, `tests/scout/test_clinical_events.py` |
| 112 | Clinical pack gate | `src/keprix/pack_gate/`, hub 202 gated install, sign-off UI, rollback, `emit_clinical_event` wiring, `tests/pack_gate/` |
| 113 | Outbound notify external | `src/keprix/notify_external/`, SMTP + signed webhooks, templates, settings UI, review gateway + pack gate integration, `tests/notify_external/` |
| 34 | Documentation site and landing page | `mkdocs.yml`, `docs/`, `scripts/generate_doc_pages.py`, `scripts/{generate,build,serve}-docs.sh`, `landing/`, `tests/docs/`, `.github/workflows/docs.yml` |
| 115 | Standalone marketing site build, deploy, analytics | `marketing/sites/keprix/`, `scripts/validate-site.sh`, `scripts/deploy.sh`, `robots.txt`, `sitemap.xml` |
| 41 | Hot backup and restore | `src/keprix/workspace/hot_backup.py`, `backup_service.py`, `scripts/keprix-backup`, `tests/security/test_backup_api.py`, `tests/workspace/test_hot_backup.py` |
| 19 | OpenAI-compatible public API and developer platform | `src/keprix/public_api/`, `/v1/chat/completions`, `/v1/responses`, `/v1/embeddings`, `/api/developer/*`, `frontend/src/app/(workspace)/developer/`, `sdk/python/`, `sdk/typescript/`, `docs/developer/`, `tests/public_api/` |
| 96 | Agent persona NEXUS orchestrator | `src/keprix/personas/nexus/`, `/api/personas/nexus/*`, `tests/personas/test_nexus_*.py` |
| 97 | Agent persona FORGE CTO / tech lead | `src/keprix/personas/forge/`, `/api/personas/forge/*`, `tests/personas/test_forge_*.py` |
| 98 | Agent persona WARDEN CISO / security | `src/keprix/personas/warden/`, `/api/personas/warden/*`, `tests/personas/test_warden_*.py` |
| 99 | Agent persona SAGE research / intelligence | `src/keprix/personas/sage/`, `/api/personas/sage/*`, `tests/personas/test_sage_*.py` |
| 100 | Agent persona BEACON marketing / delivery | `src/keprix/personas/beacon/`, `/api/personas/beacon/*`, `tests/personas/test_beacon_*.py` |
| 101 | Agent persona PRISM SEO / organic growth | `src/keprix/personas/prism/`, `/api/personas/prism/*`, `tests/personas/test_prism_*.py` |
| 102 | Agent persona COMPASS strategy / decisions | `src/keprix/personas/compass/`, `/api/personas/compass/*`, `tests/personas/test_compass_*.py` |
| 103 | Agent persona EMBER wellbeing coach | `src/keprix/personas/ember/`, `/api/personas/ember/*`, `tests/personas/test_ember_*.py` |
| 104 | Agent persona ECHO voice receptionist | `src/keprix/personas/echo/`, `/api/personas/echo/*`, `tests/personas/test_echo_*.py` |
| 105 | Agent persona CODEX legal assistant | `src/keprix/personas/codex/`, `/api/personas/codex/*`, `tests/personas/test_codex_*.py` |
| 106 | Agent persona SCOUT governance / kill switch | `src/keprix/personas/scout/`, `/api/personas/scout/*`, `tests/personas/test_scout_persona.py` |
| 83 | Research evals, reproducibility, and release map | `evals/research/`, `docs/research/reproducibility.md`, `docs/research/research-workspace-release-map.md`, `tests/integration/test_research_workspace_smoke.py` |
| 66 | Pydantic AI-style typed agents and DI | `src/keprix/typed_agents/`, `tests/typed_agents/` |
| theme-picker | Multi-skin theme switcher | `scripts/build-theme-skins.py`, `frontend/public/themes/skins.css`, `ThemePickerMenu`, `ThemeAppearancePanel`, `palette-from-css.ts` |
| agent-chat-webui | Agent chat WebUI polish | `frontend/src/components/chat/`, mobile drawer, `ModelSelector`, `SessionList`, `TypingIndicator`, `tests/frontend/test_chat_components.py` |
| terminal-ui | Terminal UI (Textual) | `src/keprix/tui/`, `keprix tui`, `tests/tui/` |
| installer-polish | Installer preflight and telemetry | `src/keprix/installer/preflight.py`, `telemetry.py`, `scripts/first-run.py`, `tests/installer/test_preflight.py`, `test_telemetry.py` |
| support-operations | Support ticket lifecycle and SLA | `src/keprix/support/lifecycle.py`, `knowledge.py`, `sla.py`, `tests/support/test_tickets_lifecycle.py` |
| managed-operations | Fleet management MVP | `src/keprix/fleet/`, `/api/fleet/*`, `tests/fleet/test_manager.py` |
| 156 | Workspace billing and subscription UI | `/settings/billing`, `frontend/src/lib/billing-api.ts`, `components/billing/`, `GET /api/billing/status`, `docs/features/billing.md`, `tests/frontend/test_billing_workspace.py` |
| 150 | Tool synthesis engine | `src/keprix/mutation/` (schema inference, synthesizer, sandbox, store), migration 016, `/api/mutation/tools/*`, `tests/mutation/test_tool_synthesizer.py`, `test_schema_inference.py`, `test_mutation_store.py` |
| 151 | Gap-to-synthesis pipeline | `mutation/hook.py`, `mutation/routes.py`, `keprix mutation` CLI, improvement wiring, `tests/mutation/test_hook.py`, `test_mutation_routes.py` |
| 152 | Prompt and persona mutation | `prompt_store.py`, `persona_mutation_store.py`, migration 017, `/api/mutation/prompts/*`, `tests/mutation/test_prompt_store.py`, `test_persona_mutation_store.py` |
| 153 | Scoped self-coding mutation | `self_coding_scope.py`, harness, git merge, `/api/mutation/code/*`, `tests/mutation/test_self_coding_*.py`, `test_code_mutation_routes.py` |
| 154 | Mutation quality and compounding | `quality.py`, `pruner.py`, `compounding.py`, retention/cron prune, `tests/mutation/test_quality_scorer.py`, `test_pruner.py`, `test_compounding.py` |
| 155 | Mutation governance UI | `/dashboard/mutation`, `mutation-api.ts`, `components/mutation/`, `tests/frontend/test_mutation_dashboard.py` |
| 157 | Deep research PDF export | `src/keprix/research/export.py`, `/api/research/jobs/{id}/export`, research report CSS, PDF cover fix in `export/renderer.py`, `/research` download buttons, `tests/research/test_research_export.py`, `docs/features/research.md` |
| 239 | Credential injection proxy (Cordon) | `src/keprix/proxy/`, `keprix proxy setup|start|doctor|env|migrate-vault|verify|route`, OAuth compat via `keprix proxy oauth`, `docs/security/credential-proxy.md`, `tests/proxy/` |
| 270 | Upgrade system core | `src/keprix/upgrade/` (check, plan, changelog, migrations, dry-run, execute, rollback, history), `keprix upgrade` CLI, `CHANGELOG.yaml`, `tests/upgrade/` |
| 272 | Cross-product upgrade | `upgrade/discovery.py`, `lockfile.py`, adoption prompts, `.keprix-lock.yaml`, enriched check output, `tests/upgrade/test_discovery.py`, `test_lockfile.py` |
| 274 | Upgrade alerts and GUI | `upgrade/alerts.py`, `notifier.py`, `events.py`, `dispatch.py`, `scheduler.py`, `service.py`, `/api/keprix/upgrade/*`, `UpgradeBanner`, `UpgradeWizardDialog`, `/settings/upgrade`, `tests/upgrade/test_events.py`, `test_alerts.py`, `test_notifier.py`, `tests/frontend/test_upgrade_workspace.py` |
| 289 | Layered system prompt architecture | `agent/layered_prompt.py`, `layered_assembly.py`, `agent/layers/*`, `system_prompt.py`, `agent.layered_prompt` config, `tests/agent/test_layered_prompt.py` |
| 291 | Provider-agnostic tool calling | `agent/tool_schema.py`, `tool_description.py`, `thinking_block.py`, `provider_normaliser.py`, `tool_audit.py`, `tools/registry.get_tool_schemas()`, `tests/agent/test_tool_*.py` |
| 290 | Persona prompt engineering | `personas/prompt_template.py`, `personas/persona_prompts/*`, `personas/persona_audit.py`, `tests/personas/test_persona_*.py` |
| 292 | Skill-first execution contract | `agent/skill_first.py`, executor hooks in `tool_executor.py`, `layers/execution.py`, `docs/features/skill-first-execution.md`, `tests/agent/test_skill_first.py` |
| 292b | Agent routing guide (OpenMontage) | `skills/personas/{nexus,warden,echo}/AGENT_GUIDE.md`, `agent/guide_enforcer.py`, NEXUS/WARDEN/ECHO mandatory preamble, `tests/agent/test_guide_enforcer.py` (filename `292-agent-routing-guide.md`) |
| 293 | Computer-use deliverable paths | `agent/deliverable_paths.py`, `tools/present_files_tool.py`, execution/computer-use guidance, gateway MEDIA auto-append, desktop present_files chip, `docs/features/computer-use-deliverables.md`, `tests/agent/test_deliverable_paths.py` |
| 294 | Deferred tool search hardening | `tools/tool_search.py` (count threshold, schema cache, DeferredToolStats), `api/tool_deferred_routes.py`, `layers/tools.py`, `docs/features/deferred-tool-search.md`, `tests/tools/test_tool_search_hardening.py` |
| 295 | Colleague memory continuity | `layers/memory_continuity.py`, `memory_edit_gate.py`, `tools/conversation_search_tool.py`, conversation_loop gates, SSN/payment privacy floors, `docs/features/colleague-memory-continuity.md`, `tests/agent/test_memory_continuity.py` |
| 296 | MCP connector-first routing | `agent/connector_router.py`, `tools/mcp_registry_tools.py`, browser soft gate, SuggestConnectorChip, `docs/features/mcp-connector-first.md`, `tests/agent/test_connector_router.py` |
| 297 | Operator-owned policy kernel | `security/operator_policy.py`, profile-aware `layers/safety.py`, CLI `keprix policy`, `api/operator_policy_routes.py`, governance UI panel, `docs/security/operator-owned-policy.md`, `tests/security/test_operator_policy.py` |
| 257 | Brain graph layout engine | `frontend/src/lib/brain/layout-*.ts`, `BrainLayoutSwitcher.tsx`, `BrainMinimap.tsx`, `ClusterBubble.tsx`, `clustering.ts`, `BrainGraphCanvas.tsx` |
| 259 | Brain health dashboard | `brain/health.py`, `duplicates.py`, `coverage.py`, `brain_health_routes.py`, `/brain/health`, `BrainHealthOverlay.tsx`, `tests/brain/test_brain_health.py` |
| 261 | Brain session replay | `brain/session_replay.py`, `brain_session_replay_routes.py`, `useBrainReplay.ts`, `BrainReplayTransport.tsx`, `BrainSessionPicker.tsx`, `tests/brain/test_session_replay.py` |
| 263 | Brain graph export and share | `brain/export_*.py`, `share_links.py`, `brain_export_routes.py`, `brain_share_routes.py`, `BrainExportMenu.tsx`, `/brain/share/[shareId]` |
| 267 | Extension architecture (Keprix variant) | `extensions/base.py`, `discovery.py`, `lifecycle.py`, `compatibility.py`, `config_merger.py`, `isolation.py`, `registry.py`, `tests/extensions/` |
| 300 | Open-amount coffee donation | `billing/stripe/checkout.py` (`price_data`), `portal/routes.py` POST `{ amount_gbp }`, `DonateCoffeeSheet.tsx`, footer, `tests/billing/test_checkout.py` |
| 371 | Memory / Brain world-class | `/api/memory/hub/*`, temporal KG + belief revision + dreaming, orchestrator in `MemoryManager.prefetch_all`, `/memory` control plane, `/v1/memory/search`, `scripts/memory_recall_benchmark.py`, `scripts/memory_eval_leaderboard.py` |

## Filed pending specs (not yet verified)

Do not treat these as completed. Canonical execution copies live in `pending-prompts/`.

| Prompt | Title | Notes |
| --- | --- | --- |
| 372 | Fail-closed prompt guard and context quarantine | Spec archived as `372-fail-closed-prompt-guard-and-context-quarantine.md` |
| 373 | Least-privilege tool ACL (lethal trifecta) | Spec archived as `373-least-privilege-tool-acl-lethal-trifecta.md` |
| 374 | RAG and Graphiti ingest poison controls | Spec archived as `374-rag-graphiti-ingest-poison-controls.md` |
| 375 | Rule of Two, human gates, honest health | Spec archived as `375-rule-of-two-human-gates-honest-health.md` |

Build order: `ref-372-llm-threat-model-hardening-build-order.md`.

## Next active prompt after 00

**371** memory world-class is archived. Active pending: `pending-prompts/data-ops-surfaces-upgrade.md` (P3 RAG + Nice/Ultimate open; P0-P2 + P4 + `/data` tabs shipped) **and** threat-model series **372-375** (parallel OK). Reference outlines **138**, **144**, **149**, and **292** remain as `ref-*.md` in this folder. Deferred polish items are documented in `PROMPT-IMPLEMENTATION-AUDIT.md`. Verification records live beside archived prompts as `*-verification.md`. Prompts 03-05 and 07 were superseded by the Hermes clone; see
`superseded-by-hermes-clone-README.md`.
