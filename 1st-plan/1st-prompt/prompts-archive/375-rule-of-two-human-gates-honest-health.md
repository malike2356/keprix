# Prompt 375: Agents Rule of Two, human gates, honest defense health

Status: COMPLETED and archived 2026-08-03 as `../prompts-archive/375-rule-of-two-human-gates-honest-health.md`  
Series: LLM threat-model hardening (ByteByteGo / Tips-and_Bits)  
Depends on: 373 profiles (preferred), checkpoints, Scout kill relay, mutation/approval UX patterns  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Even with better ACL and prompt guard, high-consequence tools (terminal, outbound notify, vault, pack install, mutation apply, wire transfer-class connectors) need a human in the loop. ByteByteGo / industry "Agents Rule of Two": an agent session should not freely combine (1) private data access, (2) untrusted content processing, and (3) external communication / irreversible side effects without a break-glass gate. Health payloads today hard-code `prompt_guard` / `tool_acl` / `checkpoint_manager` True regardless of enforcement mode, which trains operators to trust presence over posture.

## Goal

1. Enforce Rule-of-Two scoring on sessions and require human approval for consequential tools when the score is hot.  
2. Make checkpoints and approvals the default path for those tools.  
3. Report **enforcement truth** in health/doctor, not mere module importability.

## Baseline

| Piece | Path |
| --- | --- |
| Kill relay | `src/keprix/governance/kill_relay.py` |
| Conversation stop/lock | `api/conversation_routes.py` uses kill state |
| Checkpoints | CLI config `checkpoints`, gateway `/rollback`, `tools.checkpoint_manager` |
| Mutation approval | `agent/keprix/approval.py`, chat MutationCard |
| Review gateway | `src/keprix/review_gateway/` |
| Scout listener | `security/scout_listener.py` |
| Health layers | `integrations/scout_production.py` `security_layers_payload()` |
| Tool executor | `agent/tool_executor.py` |

## Must-haves

1. **Rule-of-Two session score** (`security/rule_of_two.py` or under governance):
   - Legs: `private_data`, `untrusted_content`, `external_side_effect`.
   - Update as tools run and as context is injected (RAG, email, web, vault peek).
   - When 2+ legs already true, next tool that would complete the third requires `human_approval` (or is denied if approvals disabled and fail-closed).
2. **Consequential tool registry**:
   - Tag tools: `side_effect=network|filesystem|credentials|billing|code_exec|messaging|pack`.
   - Default require approval when tag in `{credentials, billing, pack}` always; when `{network, filesystem, code_exec, messaging}` and Rule-of-Two would complete.
3. **Human approval path**:
   - Reuse existing approval/mutation/review patterns where possible (do not invent a third UI language).
   - Chat: pending card with Approve / Deny; timeout fail-closed.
   - API: 202 + approval id for `/v1` tool calls (or deny external keys from completing trifecta; prefer deny for external API keys).
4. **Checkpoints**:
   - Before approved destructive filesystem/code tools, auto-create checkpoint when checkpoints enabled; surface rollback hint on failure.
5. **Scout / kill integration**:
   - Approval denial and Rule-of-Two blocks emit Scout signals.
   - Active kill / workspace lock short-circuits approvals (no approve while killed).
6. **Honest health**:
   - `security_layers_payload()` returns structured objects, e.g.  
     `prompt_guard: {present, mode, enforced}`  
     `tool_acl: {present, base_allow_all, fail_closed}`  
     `rule_of_two: {enabled, active_sessions_hot}`  
     `checkpoint_manager: {present, enabled}`  
   - Doctor WARN if present but not enforced.
   - Update self_knowledge / ops docs that still list boolean True layers.
7. **Tests**:
   - Unit score transitions.
   - Feature: simulated session with private RAG + untrusted URL fetch cannot send email without approval.
   - Health schema tests for nested layer objects (keep backward-compatible flat aliases if needed, marked deprecated).

## Nice-to-haves

1. Operator dashboard strip: hot sessions count.
2. Policy packs from Scout that raise/lower which tags always need approval.
3. TUI approval keybinding parity with web MutationCard.

## Ultimate

1. Cryptographic attestation of approval events into Scout evidence packs.
2. Automatic session quarantine (read-only) after repeated denied escalation attempts.

## Out of scope

- Rewriting Channel Shield
- Implementing 372/373/374 from scratch (consume their modes/profiles)
- New Stripe prices (never)

## Delivery order

1. Rule-of-Two scorer + session store
2. Consequential registry + tool_executor hook
3. Approval UX/API (reuse)
4. Checkpoint pre-flight for destructives
5. Honest health + doctor
6. Docs, tests, deploy, smoke one hot trifecta denial and one approved path

## Acceptance

- [ ] Completing the third Rule-of-Two leg without approval is impossible on default profile
- [ ] External API keys cannot rubber-stamp consequential tools
- [ ] Health no longer claims "True" for unenforced layers
- [ ] Kill state blocks approvals
- [ ] Tests green; docs match enforcement

## Archive / queue pointers

- Build order: `../prompts-archive/ref-372-llm-threat-model-hardening-build-order.md`
- Prior Scout packaging: `../prompts-archive/278-security-gap-analysis.md`, `../prompts-archive/281-production-deployment-and-scout.md` (titles may vary; search archive for Scout production)
