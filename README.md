# Keprix

Path: `/opt/lampp/htdocs/verlox/keprix` (own git).
Parent workspace map: [../README.md](../README.md).

[![CI](https://github.com/malike2356/keprix/actions/workflows/ci.yml/badge.svg)](https://github.com/malike2356/keprix/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/malike2356/keprix)](https://github.com/malike2356/keprix/releases)

**Keprix** is a self-hosted AI agent OS. Run agents, playbooks, tools, memory, Channel Shield, and workflows on your own infrastructure with a full web workspace, terminal Command Center, REST API, and optional mobile client.

## What you get

| Component | Description |
| --- | --- |
| **Workspace UI** | Next.js app: chat, documents, tasks, playbooks, agent apps, settings |
| **Command Center TUI** | Textual terminal UI with chat, sessions, slash commands, runtime timeline, tool cards, debug overlay, and review mode |
| **Agent runtime** | Python backend (FastAPI): LLM routing, tools, memory, MCP, cron |
| **Mutation engine** | Keprix-only self-improvement loop for tools and skills |
| **Playbooks** | Visual and YAML workflows with runs, approvals, and schedules |
| **Agent Apps** | Manifest-driven apps from the marketplace (webhooks, billing hooks) |
| **Channel Shield** | Inbound email and messaging protection with scanning, quarantine, and policy hooks |
| **Security layer** | Vault, credential proxy, review gateway, ACLs, governance, audit logs, and Scout integration |
| **Deploy** | Docker Compose stack (Postgres, Redis, ChromaDB) |

## Quick start (Docker)

```bash
git clone https://github.com/malike2356/keprix.git
cd keprix
cp .env.example .env
# Set at least one LLM key in .env (ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY)
docker compose -f docker/docker-compose.yml up -d --build
```

Open **http://localhost:3000** for the UI. API health: `curl -s http://127.0.0.1:3333/api/health`

Full install guide: [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md)

## Local CLI install

For a workstation install with the packaged command:

```bash
pipx install '.[tui]' --force
keprix --version
keprix tui --help
```

See [docs/getting-started/install.md](docs/getting-started/install.md).

## Manual install (development)

```bash
bash scripts/install.sh
source .venv/bin/activate
```

See [docs/community/contributing.md](docs/community/contributing.md) for backend, frontend, and test commands.

## Repository layout

| Path | Purpose |
| --- | --- |
| `src/keprix/` | Python backend, CLI, agent runtime, API |
| `frontend/` | Next.js workspace and marketing shell |
| `docker/` | Production Docker images and Compose |
| `config/` | Runtime YAML (agent apps, billing, legal text) |
| `migrations/` | Alembic database migrations |
| `docs/` | Operator and developer documentation (MkDocs) |
| `tests/` | Pytest suite |
| `evals/` | Eval suites and benchmark fixtures |
| `domain-packs/` | Bundled domain skill packs |
| `mobile/` | Android client (optional) |
| `ui/design-system/` | Design tokens consumed by the frontend |
| `keprix-data/` | Local runtime data (SQLite/JSON; do not commit secrets). In this workspace it resolves to the top-level `../keprix-data` store via symlink |
| `apps-on-keprix/` | Small Keprix-built app notes / retired surfaces |
| `1st-plan/` | Active prompts and light planning only |

Large competitor research clones and UI/pitch dumps were moved out of this tree to `../archive/keprix-wip-bakups/` (see `1st-plan/MOVED-TO-BACKUP.txt`).

## Architecture boundary

Keprix keeps a stable core engine and extends it with product modules. Core runtime areas such as the agent loop, TUI, tools, memory, provider routing, sessions, and CLI dispatch should stay generic. Product areas such as Agent OS, Channel Shield, billing, Scout, agent apps, workflows, and admin dashboards extend core through registries, adapters, config, feature flags, and hooks.

See [Core and product boundary](docs/architecture/core-product-boundary.md).

## Documentation

| Topic | Link |
| --- | --- |
| Full product map | [docs/features/full-product-map.md](docs/features/full-product-map.md) |
| Quickstart | [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md) |
| Features | [docs/index.md](docs/index.md) |
| Terminal UI | [docs/features/tui.md](docs/features/tui.md) |
| REST API | [docs/reference/api.md](docs/reference/api.md) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Security | [SECURITY.md](SECURITY.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |

Browse locally: `bash scripts/serve-docs.sh` then open http://127.0.0.1:8000

## Related projects

Keprix CE is maintained alongside other products by the same developer. They are separate products with their own sites and licences:

| Product | Site |
| --- | --- |
| Keprix (this repo) | [GitHub](https://github.com/malike2356/keprix) |
| Carina (AI agent platform) | [carinaai.uk](https://carinaai.uk) |
| Aiva (managed AI workers) | [hireaiva.co.uk](https://hireaiva.co.uk) |
| Scout (governance console) | [labyrinthscout.com](https://labyrinthscout.com) |
| Propreneur (property investor OS) | [propreneur.uk](https://propreneur.uk) |
| TuinApp (workforce SaaS) | [tuinapp.uk](https://tuinapp.uk) |
| PropCalc (property calculators) | [propcalc.uk](https://propcalc.uk) |

Details: [docs/community/related-projects.md](docs/community/related-projects.md)

## Licence

MIT. See [LICENSE](LICENSE). Third-party notices: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Contact

Verlox Ltd: [contact@verlox.uk](mailto:contact@verlox.uk)
