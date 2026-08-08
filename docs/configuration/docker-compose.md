# Docker Compose

Default stack: `docker/docker-compose.yml`

## Services

| Service | Default port | Role |
| --- | --- | --- |
| keprix-frontend | 3000 | Next.js UI |
| keprix-backend | 3333 | FastAPI agent API |
| postgres | 5432 | Primary database (pgvector) |
| redis | 6379 | Cache and queues |
| searxng | 8080 | Self-hosted web search |

## Startup order

Compose `depends_on` uses health conditions: the **frontend** waits for the **backend** to be healthy; the **backend** waits for **postgres** and **redis** to be healthy. That is the default full-stack path in `docker/docker-compose.yml`.

## Customize binds

Set in `.env`:

```bash
BACKEND_BIND=127.0.0.1
BACKEND_PORT=3333
FRONTEND_BIND=127.0.0.1
FRONTEND_PORT=3000
```

Use `0.0.0.0` only on trusted networks or behind a reverse proxy.

## GPU overrides

```bash
# NVIDIA
COMPOSE_FILE=docker/docker-compose.yml:docker/gpu-nvidia.yml docker compose up -d

# AMD
COMPOSE_FILE=docker/docker-compose.yml:docker/gpu-amd.yml docker compose up -d
```

## Data volumes

Application data persists in the `keprix_data` Docker volume and `~/.keprix` bind mount.

## SearXNG only (local dev)

If you run the Keprix API outside Docker but want self-hosted web search:

```bash
docker compose -f docker-compose.searxng.yml up -d
```

Defaults: `http://127.0.0.1:8080`. Override bind/port in `.env`:

```bash
SEARXNG_BIND=127.0.0.1
SEARXNG_PORT=8080
```

Verify JSON search (required by Keprix):

```bash
curl -s "http://localhost:8080/search?q=test&format=json" | head -c 200
```

In the UI: **Settings -> Web search -> SearXNG**, set `SEARXNG_URL` to `http://localhost:8080`, then **Save**.

Config template: `docker/searxng.example/settings.yml` (JSON format enabled). Writable overrides go in `docker/searxng/` (gitignored).
