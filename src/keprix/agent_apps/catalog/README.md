# Agent Apps marketplace catalog

Curated templates ship under `catalog/{id}/` with `agent.yaml`, instructions, tools, evals, and README.

## Index

`index.json` lists marketplace metadata (category, tier, featured). The API merges optional domain-pack entries from:

```text
domain-packs/{pack_id}/agent-apps/index.json
```

Each domain-pack entry is tagged with `source: domain_pack` and `pack_id` in `GET /api/agent-apps/catalog`.

## Tiers

- `free`: installable on all plans
- `pro`: requires `agent_apps.pro_templates` (config default or billing feature flag)
