# Products Built On keprix

Downstream vertical apps and platforms in this folder **run on keprix** as the AI
backbone. They do not fork keprix. They bundle the official keprix image or call
keprix over HTTP/SDK, then add domain-specific UI, data, and workflows.

Read [../planning/prompts/00a-product-vision-and-agent-consolidation-map.md](../planning/prompts/00a-product-vision-and-agent-consolidation-map.md) for the keprix core vision.
Read [../docs/BRAND-BOUNDARY.md](../docs/BRAND-BOUNDARY.md) before mixing commercial Carina/Aiva branding.

## Build priority

keprix core must reach a **consumer-ready SDK and runtime** before these ship. Order:

| Priority | Project | Path | Why sooner |
| --- | --- | --- | --- |
| 1 | **Petraclus** | `petraclus/` | Cyber workspace; bundles keprix at `http://keprix:3333`; Pro/Team keys at `keys.petraclus.uk` |
| 2 | **AbbiS** | `abbis/` | Borehole industry SaaS (Ghana); per-stakeholder portals + domain AI on keprix |
| 3 | Fleetz | `fleetz/` | Fleet tracking + fuel monitoring (Ghana); product logic on keprix where AI is needed |
| 4 | NHS / COMPASS | `NHS/` | Continuous Compliance CI/CD (clinical safety copilot); longer regulatory path |
| 5 | **xeclone / iLaud** | `xeclone/` | Laud multimodal clone; product spec on keprix, Phase 1 social runtime on Carina Aiva |

Petraclus and AbbiS are the **first production consumers** of keprix. xeclone is a **keprix-owned product** that currently uses Carina Aiva as runtime for native social channels (see `xeclone/README.md`).

keprix v1.0 MVP decisions in `planning/prompts/00b-mvp-scope-and-build-order.md` should be judged against
what these two need, not only against generic self-host demos.

## Integration pattern (all projects)

```
┌─────────────────────────────────────┐
│  Vertical product (Petraclus, AbbiS) │
│  - Domain UI                        │
│  - Domain API + database            │
│  - Auth, billing, compliance        │
└──────────────┬──────────────────────┘
               │ keprix SDK / HTTP
               ▼
┌─────────────────────────────────────┐
│  keprix (official image or service)  │
│  - Agent loop, memory, tools        │
│  - RAG, playbooks, channels         │
│  - Mutation engine (when enabled)   │
└─────────────────────────────────────┘
```

Rules:

- **Do not fork** keprix Python into a product repo.
- **Do not** expose keprix's raw UI to end users unless the product is keprix itself.
- Domain tools that touch regulated assets (targets, patient data, fleet devices) stay in
  the product layer; keprix handles reasoning, memory, and approved automation.
- Optional [Labyrinth Scout](https://labyrinthscout.com) connector is per-product
  (Petraclus Pro/Team marketing discount; AbbiS and others at full price unless stated).

## Projects

| Project | Summary | keprix entry prompt |
| --- | --- | --- |
| [petraclus/](petraclus/) | Cybersecurity workspace (Community + Pro/Team) | `petraclus/prompts/00b-extend-from-keprix-architecture.md`, `03-keprix-sdk-integration-and-ai-backbone.md` |
| [abbis/](abbis/) | Borehole / groundwater industry platform (AbbiS 4.0 SaaS) | `abbis/reference/README.md`, `abbis/prompts/README.md`, `abbis/reference/strategy/04-carina-integration.md` (rename to keprix in implementation) |
| [fleetz/](fleetz/) | Fleet tracking and fuel theft detection | `fleetz/README.md` |
| [NHS/](NHS/) | COMPASS clinical safety / DevSecOps copilot | `NHS/SCOPE.md`, `NHS/README.md` |
| [xeclone/](xeclone/) | iLaud multimodal clone (Laud digital twin) | `xeclone/README.md`, `xeclone/HOSTING.md`; build prompts in `carina/01-devends/prompts-library/pending/aiva-social-channels--*` |

## Minimum keprix surface for Petraclus + AbbiS

Before declaring keprix "ready for consumers", these prompts should be stable:

| Prompt | Needed for |
| --- | --- |
| 00-07 | Core runtime, tools, memory, skills |
| 08 | Vault (product credentials + SDK keys) |
| 16 | REST/WebSocket API |
| 19 | Python + TypeScript SDK |
| 31-32 | Reference UI patterns (products reuse design tokens, not necessarily ship keprix UI) |
| 36 | Mutation engine (AbbiS domain packs / custom tools; optional for Petraclus v1) |
| 46 | Scout connector (optional; Petraclus Pro/Team) |

Defer for consumer v1 if not blocking: Opportunity Engine (52-63), adoption pack (64-72),
mobile apps (18), marketplace (44).

## Folder layout

```text
keprix-projects/
  README.md           <- this file
  petraclus/          <- prompts, legal, academy (build first)
  abbis/              <- reference specs + strategy (build second)
  xeclone/            <- iLaud product spec, persona, social build prompts
  fleetz/             <- strategy and planning
  NHS/                <- COMPASS scope and compasslab
```

Implementation code for each product may also live under `/opt/lampp/htdocs/verlox/`
(e.g. `abbis` deploy target). This folder holds **keprix-ai workspace** specs and prompts.

## Related repos in `keprix-ai/`

| Path | Role |
| --- | --- |
| `keprix/` | keprix agent OS (MIT) |
| `keys-server/` | `keys.petraclus.uk` (Petraclus Pro/Team only) |
| `planning/prompts/` | keprix build prompts |
| `marketing/sites/` | Standalone marketing sites (keprix, Petraclus) |

## Contact

Verlox Ltd: [contact@verlox.uk](mailto:contact@verlox.uk)
