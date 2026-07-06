# Carina feature inventory

Machine-readable source: `src/keprix/extraction/inventory.yaml`.

This inventory lists Carina core (`core.carinaai.uk`) capabilities referenced by Keprix rebuild prompts.
Each row includes subsystem, owner, source path, target prompt, classification, and rebuild plan.

## Subsystems

| Subsystem | Features | Primary Keprix prompts |
| --- | --- | --- |
| memory | pgvector RAG, episodic store | 06 |
| credentials | vault, encryption, redaction | 08 |
| workspace | documents, notes, calendar | 10 |
| gateway | provider router, cost tracking | 04 |
| api | REST, WebSocket, observability | 18 |
| skills | pack manifests, hub | 36 |
| channels | multi-channel adapters | 11 |
| tools | research and stats executors | 74 |
| mcp | integration registry | 17 |
| agents | conversation loop discipline | 03 |

## Inventory rules

1. Read Carina trees read-only; never copy `.env`, customer data, or production secrets.
2. Every feature has an owner (`platform` or `aiva`) and a `source_path` under the Carina monorepo.
3. `public_core` and `public_optional` rows must name a Keprix `target_prompt`.
4. `unsafe_or_private` rows must include `rejected_reason`.

Run validation:

```bash
.venv/bin/python -c "from keprix.extraction.report import validate_inventory; print(validate_inventory())"
```

See `carina-to-keprix-map.md` for source-to-target mapping and `extraction-rules.md` for the workflow.
