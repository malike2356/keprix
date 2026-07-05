# keprix

Open-source product workspace for **Keprix** and **Petraclus**.

**Keprix** consolidates Hermes, Carina platform patterns, OpenClaw, Odysseus, and the
expanded reference-agent set into one MIT-licensed self-hosted agent OS, with a
Keprix-only Mutation engine.

Commercial products (**Carina**, **Aiva**, **Scout**) live in `/opt/lampp/htdocs/verlox/carina/`.

Read [BRAND-BOUNDARY.md](BRAND-BOUNDARY.md) before changing naming, keys, or cross-product copy.

## Layout

| Path | Product | Licence |
| --- | --- | --- |
| `keprix/` | Keprix agent OS | MIT |
| `keprix-projects/` | Vertical products **built on Keprix** (see [keprix-projects/README.md](keprix-projects/README.md)) | Per product |
| `keprix-projects/petraclus/` | Petraclus cyber workspace | Community OSS + commercial Pro/Team |
| `keprix-projects/abbis/` | AbbiS borehole industry SaaS | Commercial (Keprix consumer) |
| `keprix-projects/fleetz/` | Fleetz fleet tracking | Commercial (planned) |
| `keprix-projects/NHS/` | COMPASS clinical safety copilot | Commercial (planned) |
| `keys-server/` | Petraclus key server (`keys.petraclus.uk`) | Private ops service |
| `planning/prompts/` | Keprix build prompts | Reference |
| `prompts-archive/` | Completed or deprecated build prompts | Reference only |

**Build priority:** Petraclus and AbbiS are the first products shipped on Keprix.
Keprix MVP scope should be validated against their SDK and backbone needs.

## Rules (short)

- No "Carina Keprix" or "Carina Petraclus" anywhere.
- Keprix has no remote licence keys and no in-app Aiva upsell.
- Petraclus Pro/Team keys use `keys.petraclus.uk`, not `keys.carinaai.uk`.
- Scout is an optional connector to both stacks, sold separately.
