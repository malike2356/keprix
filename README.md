# Keprix

[![CI](https://github.com/malike2356/keprix/actions/workflows/ci.yml/badge.svg)](https://github.com/malike2356/keprix/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/malike2356/keprix)](https://github.com/malike2356/keprix/releases)

**Keprix** is a self-hosted AI agent OS. Run agents, playbooks, tools, and workflows on your own infrastructure with a full workspace UI, REST API, and optional mobile client.

## What you get

| Component | Description |
| --- | --- |
| **Workspace UI** | Next.js app: chat, documents, tasks, playbooks, agent apps, settings |
| **Agent runtime** | Python backend (FastAPI): LLM routing, tools, memory, MCP, cron |
| **Mutation engine** | Keprix-only self-improvement loop for tools and skills |
| **Playbooks** | Visual and YAML workflows with runs, approvals, and schedules |
| **Agent Apps** | Manifest-driven apps from the marketplace (webhooks, billing hooks) |
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

## Documentation

| Topic | Link |
| --- | --- |
| Quickstart | [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md) |
| Features | [docs/index.md](docs/index.md) |
| REST API | [docs/reference/api.md](docs/reference/api.md) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Security | [SECURITY.md](SECURITY.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |

Browse locally: `bash scripts/serve-docs.sh` then open http://127.0.0.1:8000

## Licence

MIT. See [LICENSE](LICENSE). Third-party notices: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
