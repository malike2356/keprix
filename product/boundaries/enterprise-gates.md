# Enterprise and Scout gates

Scout (Labyrinth Scout) is a **separate paid product**. Keprix ships an optional connector (Prompt 38); it is never bundled.

## Classification: scout_enterprise

Features in this class:

- Require an enrolled Scout instance and API key stored in the Keprix vault
- Must not appear as free or included in Keprix marketing or default UI
- Surface only on `/settings/governance` and related admin paths

## Gated features (from inventory)

| Feature | Aiva/Carina source | Keprix surface |
| --- | --- | --- |
| Scout subscription provisioning | `billing/aiva-scout-provisioning.ts` | Scout connector enrollment |
| Governance dashboard | `app/(workspace)/aiva/governance/` | `/settings/governance` |

## Enforcement in Keprix

1. `KEPRIX_GOVERNANCE_ENABLED` and vault-stored Scout API key required before governance actions run.
2. UI contract exposes `scout` flag only when connector is configured (`ui_contract`).
3. Slash command `/scout status` reports connector state; no nag banners on unrelated pages.
4. Extraction scanner flags Scout enterprise rows; tests assert `is_scout_gated()` for inventory entries.

## Aiva commercial inclusion (not ported)

On Aiva SaaS, Scout is included with subscription. That bundling model is **not** replicated in Keprix.
Keprix operators purchase Scout separately at full price.

## Related prompts

- Prompt 37 (this boundary map)
- Prompt 38 (Scout governance bridge)
- Prompt 00a (Scout boundary table)
