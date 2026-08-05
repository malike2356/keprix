# Hermes Upstream Control Plane

Keprix tracks [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) releases as a **capability radar**, not a merge source. Automation proposes; humans approve; agents rebuild against Keprix abstractions; parity scripts prove.

## Daily check

```bash
keprix upstream check
keprix upstream review
keprix upstream decide <feature_id> --status adopt_with_hardening
keprix upstream adopt <feature_id>
# after implementation + parity gates:
keprix upstream complete <feature_id> --equivalent tools-mcp
```

Inventory state lives in `~/.keprix/upstream/hermes_inventory.yaml` (seeded from the packaged copy). Sync capabilities with:

```bash
keprix upstream sync-registry
```

Install the daily cron line:

```bash
bash scripts/install-upstream-cron.sh
# or
keprix upstream cron-install --install
```

## Approval rule

New Hermes bullets land as `unevaluated` with a `suggested_status`. Only `already_have` is auto-decided by the capability registry. `keprix upstream adopt` refuses work until `decide` sets `adopt` or `adopt_with_hardening`.

## Admin UI

Admin > Hermes upstream (`/admin/upstream`) exposes the review queue, check, decide, and generate-prompt actions via `/api/admin/upstream`.

## Work packages

Approved `adopt` writes:

1. A numbered prompt under `1st-plan/1st-prompt/pending-prompts/`
2. A YAML work package under `~/.keprix/upstream/work-packages/` with target paths, hardening checklist, and parity gates

Never merge Hermes git history into `src/keprix/`.

## Related

- [Upstream adoption policy](../architecture/upstream-adoption-policy.md)
- Parity gates: `scripts/check-tui-parity.sh`, `scripts/check-tui-surpass-hermes.sh`, `scripts/check-agent-parity.sh`
