# Keprix

[![CI](https://github.com/malike2356/keprix/actions/workflows/ci.yml/badge.svg)](https://github.com/malike2356/keprix/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/malike2356/keprix)](https://github.com/malike2356/keprix/releases)

CI and Release badges resolve for anonymous users after the GitHub repository is public.

**Keprix** is a self-hosted AI agent OS. Community Edition is MIT-licensed. Run agents, tools, memory, a Command Center TUI, and a web workspace on your own infrastructure. A mutation engine can propose tool and skill changes with human approval. Channel Shield and a vault/credential layer protect inbound channels and secrets.

## Quick Install

Stable installers and immutable terminal releases will appear at
[keprixai.com/download](https://keprixai.com/download) only after their signatures,
checksums, SBOMs, and provenance are published.

Current source installation (Linux, macOS, WSL2):

```bash
curl -fsSL https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh | bash
```

This follows the development branch and is not an immutable stable release. Review
the script before running it. See [docs/operations/public-github-checklist.md](docs/operations/public-github-checklist.md).

Then:

```bash
hash -r   # or open a new shell so ~/.local/bin is on PATH
keprix --version
keprix setup
keprix tui
```

Default home: `~/.keprix` (code at `~/.keprix/keprix`). Guide: [docs/getting-started/install.md](docs/getting-started/install.md).

Alternatives: pipx from git (see install.md); from a checkout, `pipx install '.[tui]' --force`.

## Full stack (Docker)

Secondary path for web UI + API + databases:

```bash
git clone https://github.com/malike2356/keprix.git
cd keprix
cp .env.example .env
# Set at least one LLM key
docker compose -f docker/docker-compose.yml up -d --build
```

UI: http://localhost:3000; health: `curl -s http://127.0.0.1:3333/api/health`

More: [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md)

## What you get

| Component | Description |
| --- | --- |
| Workspace UI | Next.js: chat, documents, tasks, playbooks, agent apps, settings |
| Command Center TUI | Textual terminal UI: chat, sessions, slash commands, tool cards, review |
| Agent runtime | FastAPI backend: LLM routing, tools, memory, MCP, cron |
| Mutation engine | Self-improvement loop for tools and skills (human approval) |
| Playbooks | Visual and YAML workflows with runs, approvals, schedules |
| Channel Shield | Inbound email/messaging protection, quarantine, policy hooks |
| Security | Vault, credential proxy, review gateway, ACLs, audit, Scout hooks |
| Deploy | Docker Compose (Postgres, Redis, ChromaDB) |

## Repository layout

| Path | Purpose |
| --- | --- |
| `src/` | Python backend, CLI, agent runtime, API |
| `frontend/` | Next.js workspace and marketing shell |
| `docker/` | Images and Compose stack |
| `docs/` | Operator and developer docs (MkDocs) |
| `tests/` | Pytest suite |
| `config/` | Runtime YAML samples |
| `migrations/` | Alembic migrations |
| `domain-packs/` | Bundled domain skill packs |
| `scripts/` | Installers and ops helpers |
| `examples/` | Sample usage |
| `evals/` | Eval suites and fixtures |
| `mobile/` | Optional Android client |
| `sdk/`, `keprix_sdk/` | SDK surfaces |
| `packages/`, `apps/` | Workspace packages and app services |
| `keprix-proxy/` | Credential proxy |
| `deploy/` | Deploy helpers |

`keprix-data/` and `logs/` are local runtime data (gitignored); do not commit secrets. Internal planning trees such as `1st-plan/` stay on the workstation only and are not part of this public repository.

## Documentation

| Topic | Link |
| --- | --- |
| Install | [docs/getting-started/install.md](docs/getting-started/install.md) |
| Quickstart | [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md) |
| Docs index | [docs/index.md](docs/index.md) |
| Terminal UI | [docs/features/tui.md](docs/features/tui.md) |
| REST API | [docs/reference/api.md](docs/reference/api.md) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Security | [SECURITY.md](SECURITY.md) |
| Licence | [LICENSE](LICENSE) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |

Local MkDocs: `bash scripts/serve-docs.sh` then open http://127.0.0.1:8000

Related products (separate sites and licences): [docs/community/related-projects.md](docs/community/related-projects.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/community/contributing.md](docs/community/contributing.md).

## Licence

MIT Community Edition. See [LICENSE](LICENSE). Third-party notices: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Self-host on your own infrastructure.

## Contact

Verlox Ltd: [contact@verlox.uk](mailto:contact@verlox.uk)
