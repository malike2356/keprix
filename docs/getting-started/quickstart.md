# Quickstart (Docker)

Install Keprix on your machine or VPS using Docker Compose. Expect the web interface at `http://localhost:3000` when all services are healthy. Total time: under 5 minutes on a modern machine.

## Prerequisites

| Requirement | Minimum version | Notes |
| --- | --- | --- |
| Docker Engine | 24+ | [Install Docker](https://docs.docker.com/get-docker/) |
| Docker Compose | v2 (plugin) | Comes with Docker Desktop; on Linux: `apt install docker-compose-plugin` |
| Git | Any | For cloning; or download the ZIP from GitHub |
| RAM | 2 GB free | 4 GB recommended if running a local LLM via Ollama |
| Disk | 5 GB free | For Docker images, database, and generated files |

You do **not** need Python, Node.js, or any other runtime installed locally. Everything runs inside containers.

## Step 1: Clone and configure

```bash
git clone https://github.com/malike2356/keprix.git
cd keprix
cp .env.example .env
```

Open `.env` in a text editor. The only field you must fill in before first run is at least one LLM provider key:

```bash
# Add at least one of these
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
```

Everything else has safe defaults for local development. See [Environment variables](../configuration/environment-variables.md) for the full reference.

## Step 2: Start the stack

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

This builds the frontend and backend images, then starts:

| Container | Purpose | Port |
| --- | --- | --- |
| `frontend` | Next.js web UI | 3000 |
| `backend` | FastAPI agent server | 3333 |
| `postgres` | Primary database | 5432 (internal) |
| `redis` | Session cache and queues | 6379 (internal) |
| `chromadb` | Vector store for memory | 8000 (internal) |
| `searxng` | Web search for research | 8080 (internal) |

The `--build` flag rebuilds images. On subsequent starts you can omit it: `docker compose -f docker/docker-compose.yml up -d`.

## Step 3: Wait for healthy

```bash
docker compose -f docker/docker-compose.yml ps
```

All containers should show `healthy` or `running`. The backend runs database migrations on startup; wait for it before opening the browser.

Check the API is up:

```bash
curl http://localhost:3333/api/health
# {"status":"ok","version":"..."}
```

## Step 4: Complete the setup wizard

Open `http://localhost:3000` in your browser.

The first-run wizard walks you through:

1. **Instance name** - displayed in the header and emails.
2. **Admin account** - sets the admin username and password.
3. **LLM provider** - confirm or change the provider from `.env`. You can add more providers later in the admin dashboard.
4. **Optional services** - enable Telegram bot, Discord bot, or other channels now or later.

Click **Finish setup**. You are taken to the workspace.

## Step 5: Start a conversation

Click **Chat** in the sidebar or launcher. Type a message. The agent responds using the provider you configured.

Try asking it to list your tasks, write a note, or search the web. If it encounters a task it cannot complete with its built-in tools, it will propose a [Mutation](../features/agent.md): a new tool synthesised on the spot and waiting for your approval.

## Stopping the stack

```bash
docker compose -f docker/docker-compose.yml down
```

Data is persisted in Docker volumes. It is safe to stop and restart; nothing is lost.

To also delete all data (full reset):

```bash
docker compose -f docker/docker-compose.yml down -v
```

## Updating

```bash
git pull
docker compose -f docker/docker-compose.yml up -d --build
```

The backend applies any new database migrations automatically on startup.

## Port conflicts

Edit `.env` and override the port variables:

```bash
FRONTEND_PORT=3001
BACKEND_PORT=3334
```

Then restart the stack.

## Running without Docker

If you want to run Keprix without Docker, see [Manual install](manual-install.md).

## Next steps

| What | Where |
| --- | --- |
| Connect a Telegram or Discord bot | [Messaging channels](../features/messaging.md) |
| Add more LLM providers | [LLM providers](../configuration/llm-providers.md) |
| Set up long-term memory | [Memory and RAG](../features/memory.md) |
| Create automated workflows | [Playbooks](../features/playbooks.md) |
| Invite more users | [Admin dashboard](../operations/admin-dashboard.md) |
| Expose Keprix to the internet safely | [Hardening](../security/hardening.md) |
| Build apps on the API | [SDK](../integrations/sdk.md) |

## Troubleshooting

### Containers not starting

```bash
docker compose -f docker/docker-compose.yml logs backend
docker compose -f docker/docker-compose.yml logs frontend
```

### Database connection errors

The backend waits for Postgres but there is a race condition on very slow machines. Restart the backend container:

```bash
docker compose -f docker/docker-compose.yml restart backend
```

### No LLM responses

1. Check `.env` has a valid provider key.
2. Restart the backend: `docker compose -f docker/docker-compose.yml restart backend`.
3. In the admin wizard, confirm the default provider is the one whose key you added.

### Port 3000 already in use

Set `FRONTEND_PORT=3001` in `.env` and restart. Open `http://localhost:3001` instead.

### Slow first build

The first `--build` downloads base images (~2 GB) and compiles the frontend. Subsequent starts are fast.
