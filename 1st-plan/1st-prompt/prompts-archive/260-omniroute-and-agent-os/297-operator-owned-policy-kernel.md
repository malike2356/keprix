# Keprix - Prompt 297: Operator-owned policy kernel

**Pack:** Fable-class product power (292-297)  
**Master reference:** `../prompts-archive/ref-292-fable-class-product-power-master-reference.md`  
**Depends on:** Defense-in-depth **275**, Scout product policy, layered safety **289**, hooks from **292-296**

## UI entry point

Primary location: `/admin/products/[id]` policy panel and `/settings/governance`  
Secondary locations: `keprix policy set --profile permissive`, Scout dashboard  
Empty state: "Using default profile: standard"  
Discovery trigger: none (operator only; not shown on product surfaces)  
Nav placement: Admin only

## Context

Anthropic splits Fable (public, extra dual-use measures) from Mythos (same model, fewer measures, approved orgs). Keprix should not hardcode Anthropic's product split. Keprix should expose **operator-owned profiles** that change refusal depth and autonomy while keeping hard floors and sandboxes.

This is Verlox's differentiator: the agent OS stays capable; the operator (and Scout) decide how open it is.

## What already exists (do not rebuild)

- `security/product_policy.py` (per-product Scout policies)
- `security/tool_acl.py`, egress gate, terminal/file/network gates (**275**)
- `agent/layers/safety.py` (hard floors)
- Scout listener / kill switch / incident playbooks (**278-283**)
- Governance policy receiver

## What to build

### 1. Policy profiles

```python
class OperatorPolicyProfile(StrEnum):
    STRICT = "strict"         # maximum refusals + confirmations
    STANDARD = "standard"     # default; Fable-like dual-use caution
    PERMISSIVE = "permissive" # Mythos-like research depth; sandboxes still on
```

Profile controls (examples):

| Knob | strict | standard | permissive |
| --- | --- | --- | --- |
| Dual-use technical depth | refuse | high-level only | detailed if operator-allowed |
| Package install in terminal | confirm/block | confirm | allow in sandbox |
| Browser to unknown hosts | block | egress policy | egress policy |
| Skill-first bypass | never | never | warn-once |
| Third-party MCP auto-call | never | suggest | suggest |
| Child safety / malware / weapons | always block | always block | always block |

Hard floors never change with profile.

### 2. Policy kernel

`src/keprix/security/operator_policy.py`:

- Resolve profile from: product policy → workspace setting → config.yaml → `STANDARD`
- Expose `get_operator_policy(ctx) -> OperatorPolicy`
- Feed layered safety assembly (swap dual-use paragraphs, not hard floors)
- Feed tool ACL defaults, skill-first gate, connector router

### 3. CLI and API

```
keprix policy show
keprix policy set --product aiva --profile permissive
keprix policy set --workspace default --profile strict
```

```
GET  /api/admin/policy
PUT  /api/admin/policy  { "profile": "permissive", "product_id": "..." }
```

Audit every change to Scout + local audit log.

### 4. UI

Admin panel:
- Current profile badge
- Diff of knobs
- Warning: permissive does not disable sandboxes, egress, or Scout kill switch

### 5. Tests

- Permissive cannot disable child-safety layer
- Profile change is audited
- Skill-first and connector router honor profile knobs
- Kill switch still works under permissive

## Files to create / modify

```
src/keprix/security/operator_policy.py
src/keprix/agent/layers/safety.py              # profile-aware dual-use section
src/keprix/keprix_cli/policy_cmd.py
src/keprix/api/operator_policy_routes.py
frontend: admin policy panel (minimal)
tests/security/test_operator_policy.py
docs/security/operator-owned-policy.md
```

## Acceptance criteria

- Operators can switch profiles without redeploying models.
- Hard floors remain identical across profiles.
- Sandboxes, egress, tool ACL, and Scout lockdown remain enforceable under permissive.
- Profile is visible in session debug / Scout product card.
- Docs state clearly: permissive ≠ ungoverned.

## Contact

Verlox Ltd: [contact@verlox.uk](mailto:contact@verlox.uk)
