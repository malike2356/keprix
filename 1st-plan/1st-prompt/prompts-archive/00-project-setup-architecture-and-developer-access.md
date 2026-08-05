# keprix - Prompt 00: Project Setup, Architecture, and Developer Access

## Context

Read `00a-product-vision-and-agent-consolidation-map.md` first. It defines the expanded
reference-agent consolidation model, Hermes-as-spine rules, Carina feature boundaries,
and Scout pricing.

You are building keprix, a self-hosted AI agent OS. It is NOT greenfield. It consolidates
the researched agent set into one MIT distribution, with Hermes as the cloned spine
(renamed to Keprix), Carina platform patterns for workspace and memory, and Keprix-only
capabilities (Mutation engine, Opportunity Engine).

Source trees (read before writing a single line):

| Role | Path |
| --- | --- |
| Spine (Hermes, full port) | `planning/agents-to-adopt/hermes-agent` |
| Channels and mobile (OpenClaw) | `planning/agents-to-adopt/openclaw` |
| Research workspace (Odysseus) | `planning/agents-to-adopt/odysseus` |
| Orchestration references | `planning/agents-to-adopt/{langgraph,crewai,autogen,mastra,google-adk-python,openai-agents-python}` |
| Specialist references | `planning/agents-to-adopt/{lavague,taskweaver,swe-agent,openhands,aider,browser-use,smolagents,pydantic-ai,semantic-kernel,llama-index,agno,haystack}` |
| Carina core (boundary reference) | `/opt/lampp/htdocs/verlox/carina/core.carinaai.uk` |
| Carina UI patterns (reference only) | `/opt/lampp/htdocs/verlox/carina/app.carinaai.uk` |

Output directory: `/opt/lampp/htdocs/verlox/keprix/keprix/`

## Naming Reference (authoritative - apply everywhere)

| Context | Name |
| --- | --- |
| Product name | Keprix |
| Edition label | Community Edition |
| Python package | `keprix` |
| Python module | `keprix` |
| PyPI package | `keprix` |
| npm package | `keprix` |
| TypeScript SDK package | `@keprix-ai/sdk` |
| Python SDK package | `keprix-sdk` |
| Python SDK module | `keprix_sdk` |
| Docker image prefix | `keprix` |
| Docker service names | `keprix-backend`, `keprix-frontend` |
| Environment variable prefix | `KEPRIX_` |
| CLI command | `keprix` |
| Python module invocation | `python -m keprix` |
| Home directory | `~/.keprix` |
| Data directory | `/data/keprix` |
| GitHub repository | `malike2356/keprix` |
| Companion enterprise product | Aiva (commercial, separate product) |
| Optional connector | Labyrinth Scout |

When any other prompt in this series references "carina_ce", "Carina CE", "carina-ce",
"CARINA_CE_", or "Aiva (commercial)", substitute the correct name from this table without
exception. Never introduce those deprecated names into new code, docs, or configs.

## What keprix Is

A single self-hosted distribution that anyone installs on their own server or machine. It
includes:

- The complete Hermes agent runtime (Python core), ported verbatim and renamed to Keprix (Prompt 03)
- Carina platform capabilities rebuilt in keprix: memory, RAG, vault, workspace, API patterns (Prompts 06-09, 16; boundary audit in Prompt 29)
- Odysseus research and SearXNG patterns merged into the Python backend
- OpenClaw channel adapters and mobile-facing capabilities
- Concept adoptions from the full reference-agent set (Prompts 51-73)
- keprix-only Mutation engine: synthesize, sandbox, approve, and install tools live (Prompt 28)
- Optional paid Scout governance connector (Prompt 30); never bundled free
- Local developer identity (Prompt 01); no remote licence server

## Developer Access and Owner Mode

The person who installs and owns a keprix instance is called the "developer" in this
codebase. Developer mode is local ownership, not a commercial licence.

During `keprix init`:
1. A local keypair is generated in `~/.keprix/identity/`.
2. A developer identity token is stored in `~/.keprix/identity/dev.json`.
3. `KEPRIX_DEVELOPER_MODE=true` is written to `~/.keprix/config.env`.

No Aiva Keys, no `keys.petraclus.uk`, no upgrade modals. Additional users use normal
auth (Prompt 08).

### Out of scope (commercial stack only)

These live in Carina / Aiva / Scout, not in keprix:

- Managed SaaS hosting and billing
- Aiva AI Employee product
- Multi-tenant white-label
- Blockchain trust attestation
- Cyber operations tooling (see Petraclus)

keprix may ship an **optional Scout connector** (Prompt 30). Scout is a separate paid product.

## Directory Architecture

```
keprix/
- backend/
  - agent/
  - workspace/
  - gateway/
  - providers/
  - tools/
    - generated/
  - skills/
    - generated/
  - research/
  - playbook/
  - mcp/
  - acp/
  - memory/
  - auth/
  - security/
  - keys/                          Developer identity only (Prompt 01)
  - cron/
  - api/
  - sdk/
  - builder/
  - scout_bridge/                  Optional Scout connector (Prompt 30)
  - observability/
  - config/
- frontend/                        Next.js 14 app
  - src/
    - app/                         App Router pages
    - components/                  Shared components including GatedFeature wrapper
    - lib/                         Utilities, API client, key validation client
- mobile/
  - ios/                           Swift app
  - android/                       Kotlin app
- keprix_sdk/
  - python/                        Python SDK package
  - typescript/                    TypeScript SDK package
- docker/
  - docker-compose.yml             Full stack: backend, frontend, postgres, redis, searxng
  - gpu-nvidia.yml                 NVIDIA GPU override
  - gpu-amd.yml                    AMD GPU override
- scripts/
  - install.sh                     Setup script (see Prompt 33 for the full installer)
  - update.sh                      Update script
  - migrate.sh                     Database migration runner
- docs/                            Self-host guide and env reference
- prompts/                         This folder - build instructions, not shipped in release
```

## Technology Stack

| Layer | Technology | Source |
| --- | --- | --- |
| Agent core | Python 3.11+ | Hermes |
| Workspace | Python, FastAPI | Odysseus |
| Frontend | Next.js 14, TypeScript | Aiva (commercial, separate product) |
| Mobile iOS | Swift | OpenClaw |
| Mobile Android | Kotlin | OpenClaw |
| Database | PostgreSQL 16 with pgvector extension | Aiva (commercial, separate product) |
| Cache | Redis 7 | Aiva (commercial, separate product) / Hermes |
| Web search | SearXNG (self-hosted) | Odysseus |
| LLM routing | Hermes LLM router (23 providers) | Hermes |
| Embeddings | Gemini / OpenAI fallback | Aiva (commercial, separate product) |
| Package manager (Python) | uv | Hermes |
| Package manager (JS) | pnpm | Aiva (commercial, separate product) |

## Tasks for This Prompt

### Task 1: Directory structure

Create the full directory tree shown in the architecture above. Do not populate implementation
files yet. Create `.gitkeep` in each empty leaf directory.

### Task 2: pyproject.toml

Create `keprix/pyproject.toml`:
- `name = "keprix"`
- `version = "0.1.0"`
- `requires-python = ">=3.11"`
- Merge dependencies from `hermes-agent/pyproject.toml` and `odysseus/pyproject.toml`.
- Deduplicate. Where versions conflict, take the higher version.
- Remove any dependency named "hermes" or "odysseus" (internal names).
- Add `[project.scripts]` entry: `keprix = "keprix.__main__:main"`.

### Task 3: Constants

Create `keprix/backend/config/constants.py`:

```python
PRODUCT_NAME = "keprix"
PRODUCT_VERSION = "0.1.0"
EDITION = "community"
HOMEPAGE = "https://github.com/malike2356/keprix"
DOCS_URL = "https://github.com/malike2356/keprix"
SPONSOR_NAME = "Carina"
SPONSOR_URL = "https://carinaai.uk"
SCOUT_CONNECTOR_URL = "https://labyrinthscout.com"
DEVELOPER_IDENTITY_DIR = "~/.keprix/identity"
DEVELOPER_CONFIG_DIR = "~/.keprix"
DATA_DIR = "/data/keprix"
```

No remote licence server constants. No Carina product branding in code strings.

### Task 4: docker-compose.yml

Create `keprix/docker/docker-compose.yml` that starts:
- `keprix-backend` (Python FastAPI, port 3333, depends on postgres and redis)
- `keprix-frontend` (Next.js, port 3000, depends on backend)
- `postgres` (PostgreSQL 16 with pgvector, port 5432 on host)
- `redis` (Redis 7, port 6379 on host)
- `searxng` (SearXNG, port 8080, internal only - do not expose to host)

All services on the `keprix_network` bridge network.

Volumes: `postgres_data`, `redis_data`, `keprix_data`.

Copy GPU override files from Odysseus, replacing "odysseus" with "keprix" in service
and image names, into `docker/gpu-nvidia.yml` and `docker/gpu-amd.yml`.

### Task 5: .env.example

Create `keprix/.env.example` by merging env variables from:
- `hermes-agent/cli-config.yaml.example`
- `odysseus/.env.example`
- `core.carinaai.uk/.env.production.example`

Group by section. Deduplicate. Add descriptions to each variable. Use `KEPRIX_` prefix
for all product-specific variables.

Remove all Scout native and blockchain variables. Keep optional Scout connector variables (Prompt 30).

```bash
# Developer mode - set by 'keprix init' if you are the installation owner
KEPRIX_DEVELOPER_MODE=false
```

Minimum 60 documented variables.

### Task 6: Developer identity bootstrap

Create `keprix/backend/keys/developer_identity.py`:

```python
"""
Developer identity bootstrap for keprix.
Called once during 'keprix init' when the user confirms they are the installation owner.
Generates a local keypair and a self-signed developer identity token.
No remote server is involved.
"""
```

The module must:
- Generate an RSA-2048 keypair (stored in `~/.keprix/identity/`).
- Build a JSON identity record containing: installation fingerprint, hostname hash, creation
  timestamp, version, and the public key.
- Sign the record with the private key and write it to `~/.keprix/identity/dev.json`.
- Write `KEPRIX_DEVELOPER_MODE=true` to `~/.keprix/config.env`.
- Log the action to the audit log with event type `developer_identity_created`.

The token is validated locally (no network call) by checking:
1. The signature matches the public key in `~/.keprix/identity/`.
2. The installation fingerprint in the token matches the current machine.

### Task 7: README.md

Create `keprix/README.md`:
- What keprix is (one paragraph, no emojis, no em dashes).
- Quick start: `docker compose up` (three commands).
- Manual install: `scripts/install.sh`.
- Links to `docs/`, `.env.example`.
- License: MIT.
- Sponsored by Carina (https://carinaai.uk); keprix is not a Carina product.
- Optional governance: Labyrinth Scout connector (https://labyrinthscout.com).
- No enterprise edition upsell copy.

### Task 8: SDK placeholder directories

Create `keprix/keprix_sdk/python/` and
`keprix/keprix_sdk/typescript/` with `.gitkeep` files.
Full SDK implementation is in Prompt 20.

## Acceptance Criteria

- `ls -la keprix/` shows all directories from the architecture tree.
- `docker compose -f docker/docker-compose.yml config` validates without error.
- `.env.example` has at least 60 documented variables.
- `pyproject.toml` has `name = "keprix"` and merged deps.
- `backend/config/constants.py` has `PRODUCT_NAME = "keprix"`.
- `backend/keys/developer_identity.py` exists with the described interface.
- No file in the output contains "Carina CE", "carina_ce", "carina-ce", or "CARINA_CE_".
- Running `grep -r "carina_ce\|Carina CE\|CARINA_CE" keprix/` returns no matches.
