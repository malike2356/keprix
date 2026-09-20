# Self-modification as capability mount

**Status:** Implemented (prompt 773, 2026-09-20)
**Package:** `keprix.mutation.mount`
**Depends on:** reversible plugin lifecycle (769), capability seams (768)
**API:** `/api/mutation/mounts`

## Intent

Mutation Engine proposals that change agent capabilities are expressed as
**mount / unmount** of plugins and skills (or a recorded seam Provider swap).
Approved changes apply only through `keprix.plugin_lifecycle`, so unload remains
possible. Denied proposals leave the registry untouched.

Steal the DeepSeek Harness self-modification-as-mounting *idea*. Keep Keprix
human approval (four-eyes). Do not import Cordis. Do not rewrite Soft Wall.

## Actions

| Action | Effect via 769 / seams |
| --- | --- |
| `mount_plugin` | `enable_plugin_hot` or declared-tool registration under plugin id |
| `unmount_plugin` | `disable_plugin_hot` |
| `mount_skill` | mount under `skill:<name>` ledger id |
| `unmount_skill` | disable `skill:<name>` |
| `swap_provider` | `SeamRegistry.set_active`; ledger under `mutation-mount:<id>` |

Legacy kind strings (`enable_plugin`, `disable_skill`, `swap_provider`, …) map
via `map_legacy_mutation_to_intent`.

## Approval

1. `propose(...)` → status `proposed` (trajectory stage `propose`)
2. Human `approve(approved_by=...)` with **four-eyes**: `approved_by` must differ
   from `proposed_by` (trajectory `approve` then `mount` / `unmount`)
3. Or `deny(...)` → status `denied`, **no** lifecycle registrations
4. `reverse(...)` undoes an applied mount/unmount through 769

There is **no auto-approve** for mount proposals. Soft Wall and four-eyes are
not bypassable on this path.

## Explicit bans

Mutations on this path **must not**:

- Disable or rewrite core Soft Wall / hardline
- Drop tenant RLS
- Turn Playbooks, CRM, billing, Document Vault, or Channel Shield into plugins
- Fetch unsigned remote plugins without owner policy
- Swap to unrestricted / no-policy Providers

See `banned_summary()` and `GET /api/mutation/mounts/bans`.

Prefer mounting existing plugins/skills over writing arbitrary Python into
`src/keprix/`.

## Usage

```python
from keprix.mutation.mount import MountIntent, get_mutation_mount_service

svc = get_mutation_mount_service()
proposal = svc.propose(
    MountIntent(
        action="mount_plugin",
        target_id="helper-pack",
        declared_tools=[{"name": "helper_ping"}],
    ),
    proposed_by="agent",
    trajectory_id="<optional>",
)
# deny: svc.deny(proposal.id, denied_by="operator", reason="...")
applied = svc.approve(proposal.id, approved_by="operator")
svc.reverse(applied.id, who="operator")
```

## Trajectory

When `trajectory_id` is set, stages are recorded as mutation events:
`propose` → `approve` → `mount` (or `unmount`). Recorded-session fixture
`mutation-propose-stub` asserts this sequence.

## Non-goals

- Fully autonomous self-rewrite of Keprix core
- Cordis / TypeScript rewrite
- Removing Soft Wall
- Marketplace auto-install from the internet

## Related

- Reversible lifecycle: `docs/architecture/reversible-plugin-lifecycle.md`
- Capability seams: `docs/architecture/capability-seams.md`
- Session trajectory: `docs/architecture/session-trajectory.md`
- Recorded-session tests: `docs/architecture/recorded-session-tests.md`
