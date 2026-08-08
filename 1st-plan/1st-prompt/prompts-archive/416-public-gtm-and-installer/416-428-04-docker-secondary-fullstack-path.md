# Prompt 420 / 04: Docker Compose full-stack as secondary path

**Status: COMPLETED 2026-08-07**  

Series: Keprix public GTM + Hermes install parity  
Depends on: 419  
Blocks: 426  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Purpose

Keep Docker Compose as the **full stack** path (web UI + API + Postgres +
Redis), clearly secondary to the curl/CLI primary path, with accurate commands
and no Verlox-absolute paths.

## Tasks

1. Update `docs/getting-started/quickstart.md` to:
   - Lead with "Option A: curl installer (CLI/TUI)" linking to install.md.
   - "Option B: Docker Compose (full web stack)" with:
     ```bash
     git clone https://github.com/malike2356/keprix.git
     cd keprix
     cp .env.example .env
     docker compose -f docker/docker-compose.yml up -d --build
     ```
   - State ports: UI `http://localhost:3000`, API health
     `http://127.0.0.1:3333/api/health`.
2. Align marketing `HowItWorks` / getting-started snippets with the same
   commands (https clone URL complete). Prefer pointing marketing "Deploy"
   step at curl one-liner if that is primary GTM story; keep Compose as
   "full stack" step or FAQ.
3. Confirm Compose `depends_on` behavior is documented: frontend waits for
   backend health (full stack). Note that marketing-only frontend separation
   is possible for operators (cross-link 427) but not the default Compose file.
4. Ensure `.env.example` lists minimum LLM keys and does not embed secrets.
5. VPS/production Compose+Caddy remains in `docs/operations/vps-deploy.md`
   (already from 369); add a one-line link from quickstart.


## What was built

- Rewrote `docs/getting-started/quickstart.md` with Option A (curl CLI/TUI) and Option B (Docker Compose full stack).
- Documented Compose `depends_on` health order; linked VPS deploy and docker-compose reference.
- Aligned marketing HowItWorks Deploy step and docs `INSTALL_CMD` with curl primary + Compose secondary.
- README Quick start points at Option A/B; `.env.example` LLM minimum comment; Startup order note in docker-compose.md.
- Gap map: Docker secondary path DONE (420).

## Acceptance

- [x] Quickstart distinguishes CLI-primary vs Docker-full-stack.
- [x] Clone URL includes `https://`.
- [x] No `/opt/lampp/htdocs` in quickstart.
- [x] Health curl examples document `http://127.0.0.1:3333/api/health` (CI does not require a running stack).

## Verification

```bash
rg -n 'https://github.com/malike2356/keprix' docs/getting-started/quickstart.md
rg -n 'docker compose -f docker/docker-compose.yml' docs/getting-started/quickstart.md README.md
rg -n '/opt/lampp/htdocs' docs/getting-started/quickstart.md && exit 1 || exit 0
```
