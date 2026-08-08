# Quickstart

See also [Install](install.md) and [First run](first-run.md).

Keprix has two install paths. The **CLI / TUI** path (Option A) is primary for day-to-day agent use. **Docker Compose** (Option B) is the full web stack path (UI + API + Postgres + Redis and related services).

## Option A: curl installer (CLI / TUI)

See [Install](install.md) for the full guide.

```bash
curl -fsSL https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh | bash
```

The public GitHub repository is anonymously readable. This command follows the
development channel. For immutable stable releases, download and inspect
`scripts/install-release.sh`, then run it with an exact `--version`.

Next steps after install:

```bash
keprix --version
keprix setup
keprix tui
```

## Option B: Docker Compose (full web stack)

Use this when you want the browser workspace plus the API and databases on one machine.

### Prerequisites

| Requirement | Minimum | Notes |
| --- | --- | --- |
| Docker Engine | 24+ | [Install Docker](https://docs.docker.com/get-docker/) |
| Docker Compose | v2 plugin | Docker Desktop includes it; on Linux: `apt install docker-compose-plugin` |
| Git | Any | For cloning |
| RAM | 2 GB free | 4 GB recommended if you also run a local LLM |
| Disk | 5 GB free | Images, database, and generated files |

You do not need Python or Node.js on the host. Everything runs in containers.

### Start the stack

```bash
git clone https://github.com/malike2356/keprix.git
cd keprix
cp .env.example .env
# Set at least one of ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY
docker compose -f docker/docker-compose.yml up -d --build
```

Copy values from `.env.example`. Leave unused keys empty; set at least one provider key before first run (for example `ANTHROPIC_API_KEY=` or `OPENAI_API_KEY=your-key-here`). Do not paste real secrets into docs or tickets.

| Surface | URL / check |
| --- | --- |
| Web UI | `http://localhost:3000` |
| API health | `curl -s http://127.0.0.1:3333/api/health` |

Compose `depends_on` (default full stack): the **frontend** waits until the **backend** healthcheck passes; the **backend** waits until **postgres** and **redis** are healthy. That is the default `docker/docker-compose.yml` behavior.

Marketing-only frontend on Contabo/Cloudflare is optional and not the default Compose stack. See [Cloud deploy](cloud-deploy.md) and [VPS deploy](../operations/vps-deploy.md). Public origin notes may expand later.

### Wait until healthy

```bash
docker compose -f docker/docker-compose.yml ps
```

Containers should show `healthy` or `running`. The backend runs migrations on startup; wait for health before opening the UI.

```bash
curl -s http://127.0.0.1:3333/api/health
# Expect JSON with a status field when the API is up
```

### Setup wizard

Open `http://localhost:3000`. The first-run wizard covers instance name, admin account, LLM provider confirmation, and optional channels. After **Finish setup**, use **Chat** in the sidebar to talk to the agent.

### Stop and update

```bash
docker compose -f docker/docker-compose.yml down
```

Data lives in Docker volumes; stop/restart keeps it. Full reset (deletes volumes):

```bash
docker compose -f docker/docker-compose.yml down -v
```

Update:

```bash
git pull
docker compose -f docker/docker-compose.yml up -d --build
```

Migrations apply on backend startup.

### Port conflicts

In `.env`:

```bash
FRONTEND_PORT=3001
BACKEND_PORT=3334
```

Then restart the stack.

### Production VPS

For Compose behind Caddy on a VPS, see [VPS deploy](../operations/vps-deploy.md). Compose service reference: [Docker Compose reference](../configuration/docker-compose.md).

### Troubleshooting

**Logs**

```bash
docker compose -f docker/docker-compose.yml logs backend
docker compose -f docker/docker-compose.yml logs frontend
```

**Database connection errors**

On very slow hosts, restart the backend after Postgres is healthy:

```bash
docker compose -f docker/docker-compose.yml restart backend
```

**No LLM responses**

1. Confirm `.env` has at least one provider key set.
2. `docker compose -f docker/docker-compose.yml restart backend`
3. In the wizard or admin UI, confirm the default provider matches that key.

**Port 3000 in use**

Set `FRONTEND_PORT=3001` and open `http://localhost:3001`.

**Slow first build**

The first `--build` downloads base images and compiles the frontend. Later starts are much faster.

### Without Docker

CLI/TUI without Compose: [Install](install.md). Manual contributor setup: [Manual install](manual-install.md).

### Next steps

| What | Where |
| --- | --- |
| Messaging channels | [Messaging](../features/messaging.md) |
| More LLM providers | [LLM providers](../configuration/llm-providers.md) |
| Memory / RAG | [Memory](../features/memory.md) |
| Playbooks | [Playbooks](../features/playbooks.md) |
| Hardening | [Hardening](../security/hardening.md) |
| SDK | [SDK](../integrations/sdk.md) |
