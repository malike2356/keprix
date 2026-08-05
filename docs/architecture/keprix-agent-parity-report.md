# Keprix Agent Parity Report

Agent parity reviewed against the Hermes Agent reference tree. Inventory
completed 2026-07-12. Prompts 327-334 were archived before this verification
pass. Re-proofed 2026-07-27 as part of private OSS ship-ready prompts 365-370.

## Executive Summary

Keprix core agent runtime is broadly aligned with Hermes Agent in the areas
listed below. The current repo has a local parity gate and focused tests for
architecture, compatibility, TUI, package entry points, and deterministic
agent smoke behavior.

**2026-07-27 gate evidence (this workspace):**

- `bash scripts/check-agent-parity.sh` -> 10/10 passed
- `bash scripts/check-tui-parity.sh` -> TUI parity contracts 100/100 passed
- `bash scripts/check-tui-surpass-hermes.sh` -> surpass contracts passed
- `bash scripts/check-private-ship-gate.sh` -> private ship gate passed
- Frontend `npx tsc --noEmit` -> exit 0
- `.venv/bin/python -m pytest tests/api -q` -> 86 passed, 2 skipped

Focused auth, billing, architecture, TUI, agent, and API suites are green in
this pass. Prefer `scripts/check-private-ship-gate.sh` before a private tag.

Keprix deliberately differs in surface UI/UX, product architecture, visual
identity, and branding. These are intentional product decisions, not gaps.

## Parity Areas Reviewed

| Area | Status |
|---|---|
| 1. Agent Loop | Keprix better |
| 2. Tool Dispatch | Same |
| 3. Prompt Assembly | Same |
| 4. Provider Routing | Same |
| 5. Streaming | Same |
| 6. Retry and Recovery | Same |
| 7. Session Persistence | Same |
| 8. Memory | Same |
| 9. Checkpoints | Same |
| 10. File Edits | Same |
| 11. Terminal Execution | Same |
| 12. Approval Flow | Same |
| 13. Skills | Same |
| 14. Plugins | Same |
| 15. MCP | Same |
| 16. Gateway | Blocked by product boundary |
| 17. Cost and Rate Handling | Same |

## Keprix-Better Areas

Keprix extends the Hermes baseline in these areas:

- **Layered prompt assembly:** Ordered prompt layers (identity, budget, safety,
  tools, tone, execution, memory continuity, domain, persona, product) with
  opt-out per layer.
- **Agent loop modularization:** 5,467-line monolith decomposed into
  conversation_loop, turn_context, turn_retry_state, tool_executor, errors,
  and prompt_builder modules.
- **Memory edit gate:** Blocks false confirmation when the memory tool
  wasn't actually called (Prompt 295).
- **Connector router:** Prefers MCP connectors over browser scraping for
  intent-matched queries (Prompt 296).
- **Product hook system:** Before-tool, after-tool, and after-turn hooks
  via `registries.product_hooks` with error isolation per hook.
- **Product prompt layers:** Product modules register prompt layers at
  runtime via `register_product_prompt_layer()` with enable/disable support.
- **Memory continuity layer:** Stable-tier memory context injected via the
  layered prompt system.
- **Domain layers:** Context-specific prompt injections for code, legal,
  medical, and property domains.
- **Ponytail ladder:** Seven-rung minimal-code generation enforced via
  `agent/ladder.py` and `agent/ladder_mode.py`.
- **Persona engineering:** 10 typed personas (NEXUS, FORGE, WARDEN, SAGE,
  BEACON, COMPASS, PRISM, EMBER, ECHO, CODEX) with routing guide enforcement.
- **Provider normaliser:** Multi-provider tool schema conversion (Anthropic,
  OpenAI, Google formats).
- **Tool ACL per product:** Tool access control lists scoped by product
  context, enforced via `security/tool_acl.py`.
- **Network egress policy:** Per-product network restrictions enforced
  via `security/egress_policy.py`.
- **Resource quotas:** Fairness scheduler for compute and token budgets.

## Deliberate Differences

These are intentional, not gaps:

- **TUI:** Keprix uses Python Textual. Hermes uses TypeScript Ink.
- **Gateway:** Channel Shield owns gateway session management in Keprix.
  Hermes gateway is a monolith.
- **Visual identity:** Keprix has its own branding, navigation, color
  system, and surface UI. Hermes identity is preserved only in attribution
  and upstream references.
- **Desktop app:** Hermes ships a desktop Tauri app. Keprix has a
  separate app under `apps/`.
- **Product architecture:** Keprix has a core/product boundary enforced
  by import tests. Hermes has no such boundary.

## Compatibility Notes

- **State paths:** `.keprix` is the primary state directory. `.hermes` is
  readable for migration compatibility. `KEPRIX_*` env vars preferred;
  `HERMES_*` accepted as fallback.
- **Binary names:** `keprix` is the entry point. Legacy `hermes` references
  in upstream tracking modules preserved for monitoring.
- **Config:** Old config at `.hermes/config.yaml` is readable. New writes
  go to `.keprix/config.yaml`.
- **Checkpoints:** Ref path migrated from `refs/hermes/` to `refs/keprix/`.

## Product Extensions Preserved

Keprix product modules are cleanly isolated from core agent runtime:

- Channel Shield: safe content, memory guard, channel config
- Agent OS: run ledger, glass panel, mutation hooks
- Scout: governance, telemetry, policy signals, evidence packs
- Billing: wallet enforcer, rate limiting, usage tracking
- Agent Apps: workspace runtime, built app shell
- Brain: graph viz, session replay, health dashboard
- Voice: Twilio handler, VAD pipeline, TTS client
- Playbooks: canvas compiler, variable context, NL builder
- Extensions: product isolation, lifecycle hooks, config merging

## Keprix UI/UX Identity Preserved

Keprix has its own:
- Navigation system with sidebar and top bar
- Color theme and CSS aliases
- Launcher with skill cards
- Admin dashboard
- Marketing site and docs
- Onboarding flow
- Authentication pages

Hermes visual identity (logos, branding, desktop app shells) is NOT copied.
Upstream attribution is explicit in docs and license.

## Test Evidence

```bash
bash scripts/check-agent-parity.sh
python -m pytest tests/architecture/test_core_product_boundaries.py \
  tests/config/test_hermes_compatibility.py \
  tests/config/test_doctor_hermes_compatibility.py \
  tests/cli/test_package_entrypoint.py \
  tests/tui tests/parity -q

# Focused verification observed in this audit cycle:
#   145 passed
```

## TUI comparison and surpass

Keprix TUI targets Hermes **behavior** parity and then surpasses Hermes in
Command Center, runtime timeline, tool cards, and operator proof harnesses.
Visual identity stays Keprix (Textual theme, copy, layout). See:

- `docs/architecture/tui-hermes-behavior-parity-contract.md`
- `docs/architecture/tui-surpass-hermes-contract.md`
- `docs/features/tui.md` (parity matrix)

## Remaining Gaps

No specific Hermes-better core behavior is currently identified as an
untracked blocker in the inventory. Remaining risk is test depth and release
confidence:

- The parity eval suite is deterministic smoke coverage and should be
  strengthened against real agent loop, tool dispatch, checkpoint, memory,
  and product hook code paths.
- Prefer `scripts/check-private-ship-gate.sh` for private soft-ship checks.
- Public GTM still needs legal entity fill, live domain proof, and a clean
  tagged release cut separate from a dirty working tree.
