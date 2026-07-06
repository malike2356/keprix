# keprix

[![CI](https://github.com/malike2356/keprix/actions/workflows/ci.yml/badge.svg)](https://github.com/malike2356/keprix/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/malike2356/keprix)](https://github.com/malike2356/keprix/releases)

Open-source product workspace for **Keprix** and **Petraclus**.

**Keprix** is an MIT-licensed self-hosted agent OS that consolidates proven agent
platform patterns into one distribution, with a Keprix-only Mutation engine.

Commercial products (**Carina**, **Aiva**, **Scout**) live in `/opt/lampp/htdocs/verlox/carina/`.

Read [BRAND-BOUNDARY.md](BRAND-BOUNDARY.md) before changing naming, keys, or cross-product copy.

## Quickstart

One-command install (bare metal):

```bash
git clone https://github.com/malike2356/keprix.git
cd keprix
bash scripts/install.sh
source .venv/bin/activate
```

Start the API and open the frontend dev server per [docs/community/contributing.md](docs/community/contributing.md).

**Agent Apps** are manifest-driven workflows you install from `/agent-apps` (marketplace templates, schedules, webhooks, and billing limits). Operator guide: [docs/features/agent-apps.md](docs/features/agent-apps.md).

## Documentation

| Resource | Link |
| --- | --- |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Community guide | [docs/community/contributing.md](docs/community/contributing.md) |
| Security | [SECURITY.md](SECURITY.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |
| Third-party notices | [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) |
| Build prompts | [planning/prompts/](planning/prompts/) |

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

## Licence

MIT. See [LICENSE](LICENSE).
