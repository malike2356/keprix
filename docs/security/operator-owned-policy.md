# Operator-owned policy profiles

Operators choose how open Keprix is without redeploying models. Profiles change
refusal depth and autonomy knobs. They never disable hard floors, sandboxes,
egress policy, tool ACL, or the Scout kill switch.

**Permissive is not ungoverned.**

## Profiles

| Profile | Intent |
| --- | --- |
| `strict` | Maximum refusals and confirmations |
| `standard` | Default; Fable-like dual-use caution |
| `permissive` | Mythos-like research depth; sandboxes still on |

### Knobs

| Knob | strict | standard | permissive |
| --- | --- | --- | --- |
| Dual-use technical depth | refuse | high-level | detailed (operator-allowed) |
| Package install in terminal | block | confirm | allow in sandbox |
| Browser to unknown hosts | block | egress policy | egress policy |
| Skill-first bypass | never | never | warn-once |
| Third-party MCP auto-call | never | suggest | suggest |
| Child safety / malware / weapons | always block | always block | always block |

## Resolution order

1. Product Scout policy (`security_profile` / `governance.operator_profile`)
2. Workspace setting (`~/.keprix/operator_policy.json`)
3. `config.yaml` (`agent.operator_policy_profile` or `security.operator_profile`)
4. `standard`

## CLI

```bash
keprix policy show
keprix policy set --profile permissive
keprix policy set --product aiva --profile strict
keprix policy set --workspace default --profile standard
```

## API

```
GET  /api/admin/policy
PUT  /api/admin/policy  { "profile": "permissive", "product_id": "..." }
```

Admin auth required. Every change is audited locally and emitted to Scout as
`operator_policy.changed`.

## UI

`/settings/governance` shows the current profile badge, knob matrix, and a
warning that permissive does not disable sandboxes, egress, or Scout kill
switch. Scout product policy cards also include `operator_policy`.

## Runtime wiring

- Safety layer: hard floors fixed; dual-use paragraph swaps by profile
- Skill-first gate: permissive uses warn-once; strict/standard never bypass
- Connector router: strict never suggests third-party MCP connect; still prefers
  already-connected connectors
- Agent init stamps `_operator_policy` / `_skill_first_profile` from the kernel

## Related

- `src/keprix/security/operator_policy.py`
- Defense-in-depth (275), Scout product policy, layered safety (289)
- Skill-first (292), connector-first (296)
