# Prompt 373: Least-privilege tool ACL (break the lethal trifecta default)

Status: COMPLETED and archived 2026-08-03 as `../prompts-archive/373-least-privilege-tool-acl-lethal-trifecta.md`  
Series: LLM threat-model hardening (ByteByteGo / Tips-and_Bits)  
Depends on: `tool_acl.py`, `tool_acl_gate.py`, `agent/tool_executor.py`, egress gate  
Related: 372 (prompt guard), 375 (human gates / Rule of Two)  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

ByteByteGo "lethal trifecta": private data + untrusted content + outbound exfil in one agent is where damage happens. Keprix `ToolACL` explicitly documents base product `keprix` as **allow-all unless denied**. Default workspace agents can therefore hold private memory/RAG, read untrusted web/email/files, and call outbound tools in one session. Channel-facing products may be stricter; the main product is not.

## Goal

Make the default Keprix agent **deny-by-default with a curated allowlist**, keep dangerous combinations impossible without an explicit elevated profile, and keep ACL checks on every tool dispatch (already partially wired).

## Baseline

| Piece | Path |
| --- | --- |
| ACL core | `src/keprix/security/tool_acl.py` (`BASE_PRODUCT` allow-all) |
| Gate | `src/keprix/security/tool_acl_gate.py` |
| Executor hook | `src/keprix/agent/tool_executor.py` |
| Admin UI | `/admin/tool-acl`, `api/tool_acl_routes.py` |
| Egress | `egress_gate.py`, `egress_policy.py`, `network_gate.py` |
| Resource scopes | `security/resource_scopes/enforce.py` |
| Public API tools | `public_api/auth.py` `check_tool_permission` |

## Must-haves

1. **Change base product default**:
   - Stop implicit `keprix` allow-all.
   - Ship a versioned default allowlist (read-only + safe search + memory read + non-mutating workspace tools).
   - Explicit deny list always includes: unrestricted terminal, arbitrary network fetch, credential vault dump, mail send, destructive file ops, code_exec with network, pack install, mutation install (unless elevated profile).
2. **Agent profiles** (config + API):
   - `assistant` (default): safe allowlist, no outbound + private write combo.
   - `researcher`: may fetch web but must not read vault secrets or send email in same profile.
   - `operator` / `coding`: terminal + file write; requires workspace flag + optional Scout policy.
   - Document that no default profile may hold all three trifecta legs without human elevation (375 implements the gate UX; this prompt owns ACL matrix).
3. **Enforce on every dispatch**:
   - Confirm `evaluate_tool_acl_gate` cannot be skipped for chat, slash-driven tools, cron agents, or `/v1` tool calls.
   - Fail closed on ACL store load errors when `KEPRIX_TOOL_ACL_FAIL_CLOSED=1` (default on).
4. **Egress coordination**:
   - Tools that dial the network must also pass egress allowlist; ACL allow of `web:*` is not enough alone.
   - Add regression test: allowed tool name + blocked host => deny.
5. **Migration / compatibility**:
   - Preserve ability for operators to `allowed_tools: ["*"]` explicitly in admin UI (loud warning banner).
   - Existing product ACLs (Aiva, etc.) unchanged unless they relied on inheriting keprix allow-all.
6. **Tests + docs**:
   - Matrix unit tests for profiles × tool names.
   - Update `docs/security/` with trifecta table and default profile matrix.
   - Admin tool-acl page shows active profile and whether allow-all is in effect.

## Nice-to-haves

1. Per-session temporary elevation token (TTL, audit, Scout signal).
2. Auto-suggest ACL tighten from audit log ("these tools unused for 30d").
3. TUI `/acl` status line mirroring health.

## Ultimate

1. Continuous Agents Rule of Two scorer that soft-blocks when session context already holds private + untrusted and the next tool is outbound (ties to 375).
2. Cross-product ACL templates published via Scout policy registry.

## Out of scope

- Prompt injection heuristics (372)
- RAG ingest scanning (374)
- Full human approval UI (375 owns that; this prompt only ensures ACL denials are decisive)

## Delivery order

1. Define default profiles + YAML/JSON seed
2. Flip `ToolACL` base product behavior + migration notes
3. Harden fail-closed in gate + executor coverage audit
4. Egress cross-check tests
5. Admin UI warning for `*`
6. Docs + deploy backend + smoke: default chat cannot `terminal:run` / send email without elevation

## Acceptance

- [ ] Fresh install: base `keprix` product is not allow-all
- [ ] Default assistant cannot complete private_data + untrusted_fetch + outbound_exfil in one profile without elevation
- [ ] Explicit `*` still works but is audited and UI-warned
- [ ] ACL + egress double gate proven by tests
- [ ] No silent skip paths in chat / cron / `/v1` tool execution

## Archive / queue pointers

- Build order: `../prompts-archive/ref-372-llm-threat-model-hardening-build-order.md`
- Prior: `../prompts-archive/275-security-defense-in-depth.md`
