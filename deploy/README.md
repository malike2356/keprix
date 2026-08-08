# Deploy helpers

Pointers for operators. This prompt does not move files (avoids breaking scripts).

## Primary Compose (strangers and day-to-day)

Use [`docker/docker-compose.yml`](../docker/docker-compose.yml) as the primary
Docker Compose path for self-host and contributor setups.

## Contabo marketing origin (keprixai.com)

Cloudflare + shared Carina nginx (not Caddy). See
[`docs/operations/keprixai-com-origin.md`](../docs/operations/keprixai-com-origin.md)
and [`deploy/contabo/`](contabo/).

## Optional root Compose overlays

Root `docker-compose.*.yml` files (for example ml, searxng, localization) are
optional overlays. Prefer the primary path above unless docs for a specific
overlay say otherwise.

## Fly.io

Fly configs live at the repo root:

- `fly.toml`
- `fly.fullstack.toml`
- `fly.backend-only.toml`

Additional Fly helpers may also live under [`deploy/fly/`](fly/).

Do not relocate these files casually; many scripts and docs assume the current
layout.
