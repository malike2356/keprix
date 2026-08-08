# keprix - Prompt 40: Rebranding, Productization, and Release Prep

## Context

Read `00a-product-vision-and-agent-consolidation-map.md`. After this sweep, no operator-facing
surface may reference Hermes, OpenClaw, Odysseus, or upstream repo URLs.

This is the FINAL prompt for v1.0 branding. All foundation prompts (00-20, 31-36, 41-46, 50)
must be complete before this one runs. Run this prompt last as the final brand and release sweep.
After prompts 52-72 are also complete, run this prompt again to sweep those additions.

This prompt handles:
1. Final brand sweep (remove all traces of Hermes, OpenClaw, Odysseus, and any
   old "Carina CE" references from user-visible text)
2. License and attribution (MIT with AGPL service boundary note)
3. Docker image finalization
4. Install script
5. Self-update mechanism
6. Documentation
7. First-run experience
8. Release checklist verification

## Execution Order

This prompt is intentionally numbered 16 but runs AFTER prompts 17 (SDK),
18 (keprix Agent), and ideally after prompts 37-46 and 50. The brand sweep in this
prompt must cover all code written by all prior prompts.

## Brand Sweep

Run a comprehensive search across the entire `keprix/` directory.
Fix every instance found:

### String replacements (case-sensitive, exhaustive):

| Find | Replace |
|---|---|
| `hermes-agent` | `keprix` |
| `hermes_agent` | `keprix` |
| `Hermes Agent` | `keprix` |
| `hermes` (standalone word, not Greek myth or third-party lib name) | `keprix` |
| `HERMES_` (env var prefix) | `keprix_` |
| `~/.hermes` | `~/.keprix` |
| `hermes onboard` | `keprix setup` |
| `hermes gateway` | `keprix gateway` |
| `hermes model` | `keprix model` |
| `hermes cron` | `keprix cron` |
| `openclaw` | `keprix` |
| `OpenClaw` | `keprix` |
| `OPENCLAW` | `keprix` |
| `openclaw.ai` | `carinaai.uk` |
| `Odysseus` (in app strings and UI) | `keprix` |
| `odysseus-ai` | `keprix` |
| `pewdiepie-archdaemon/odysseus` | `malike2356/keprix` |
| `github.com/openclaw/openclaw` | `github.com/malike2356/keprix` |
| `Carina CE` | `keprix` |
| `carina_ce` (module/package/dir) | `keprix` |
| `carina-ce` (package/docker name) | `keprix` |
| `CARINA_CE_` (env var prefix) | `keprix_` |
| `carina_ce_sdk` | `keprix_sdk` |
| `@carina-ce/sdk` | `@keprix-ai/sdk` |
| `carina-ce-sdk` | `keprix-sdk` |
| `carina-ce tools` | `keprix tools` |
| `Aiva (commercial)` (in user-visible strings) | `Aiva (commercial, separate product)` |

### Do NOT rename in:
- THIRD_PARTY_NOTICES.md (legal compliance file only - original copyright notices are
  required under MIT licence; this file is not user-facing and is not part of the app)
- Python package imports from third-party libraries named after the source projects
- Git history

### Remove everywhere else, including:
- All code comments that explain provenance ("ported from Hermes", "based on OpenClaw",
  "derived from Odysseus" etc). Rewrite as functional comments or remove entirely.
- Any variable, class, function, or module name that contains hermes, openclaw, or odysseus.
- Any string literal in the application that contains these names.
- Any environment variable name, config key, or CLI argument that references them.

### Files that must show ONLY keprix branding in their user-visible strings:
- All `*.py` files in `backend/`
- All `*.ts`, `*.tsx` files in `frontend/src/`
- All `*.swift` files in `mobile/ios/`
- All `*.kt` files in `mobile/android/`
- All `*.py`, `*.ts` files in `keprix_sdk/`
- `README.md`, `docs/`, `docker-compose.yml`, `.env.example`

## License and Attribution

### License

keprix is MIT licensed in its entirety: backend, frontend, SDK, mobile, scripts.
There is no AGPL layer. The whole project is given back to the community under MIT.

Create `keprix/LICENSE`:
```
MIT License

keprix
Copyright (c) 2026 Verlox Limited

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Third-Party Notices

Create `keprix/THIRD_PARTY_NOTICES.md`.

This file fulfils the copyright-preservation requirement of MIT licences covering
source code incorporated during development. It is a legal compliance file only.
It must NOT be linked from the application UI, must NOT appear in onboarding flows,
and must NOT be used as marketing material.

Include:
- One section per source codebase incorporated. For each: original copyright
  holder(s), year(s), and the full text of their MIT licence notice. Do not include
  project names in any user-visible part of the application itself.
- One section listing all third-party Python dependencies and their licences
  (generate with `pip-licenses --format=markdown`).
- One section listing all Node.js dependencies and their licences
  (generate with `pnpm licenses list --json`).

Do NOT create `ACKNOWLEDGMENTS.md`, `LICENSE-AGPL.txt`, or `LICENSE-MIT.txt`.
The `LICENSE` file and `THIRD_PARTY_NOTICES.md` are the only attribution files needed.

## Self-Host Activation

keprix is free to use. No license key required. Show a non-intrusive
attribution:

In the web UI footer:
```
keprix - Community Edition - VERLOX Ltd - carinaai.uk
```

In the CLI startup banner (this exact text):
```
keprix v1.0.0 - The keprix Agent
Community Edition - VERLOX Ltd - https://carinaai.uk
Governance: Labyrinth Scout - labyrinthscout.com
```

No usage telemetry without explicit opt-in.
`keprix_TELEMETRY=false` (default). If `true`, send anonymous usage counts
to `telemetry disabled by default` (basic: version, OS, provider count, message count).
Never send conversation content, API keys, or personal data.

## Docker Image

`keprix/docker/Dockerfile.backend`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev gcc curl git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

COPY backend/ ./backend/
COPY locales/ ./locales/

ENV keprix_DATA_DIR=/data
VOLUME ["/data"]

EXPOSE 3333

CMD ["python", "-m", "keprix", "start", "--host", "0.0.0.0", "--port", "3333"]
```

`keprix/docker/Dockerfile.frontend`:
```dockerfile
FROM node:22-slim AS builder
WORKDIR /app
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM node:22-slim
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

`keprix/docker/Dockerfile.sdk` (publish SDK as a separate image):
```dockerfile
FROM python:3.11-slim
WORKDIR /sdk
COPY keprix_sdk/python/ .
RUN pip install uv && uv sync --frozen
```

The final `docker-compose.yml` (from Prompt 00) builds backend + frontend images.

## Install Script

`keprix/scripts/install.sh` (finalize here):
- Auto-detect OS (Ubuntu/Debian/macOS/Arch)
- Install Docker + Docker Compose if not present
- Clone or download the repo
- Generate `.env` from `.env.example` with prompted values (admin password, first provider key)
- Run `docker compose up -d --build`
- Wait for health check (`GET /api/health` returns 200)
- Print: "keprix is running at http://localhost:3000"
- Print the CLI banner text so the user sees it on first install

One-liner install:
```bash
curl -fsSL https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh | bash
```

Create `keprix/scripts/install-curl.sh` to be served at that URL.

## Self-Update

`backend/cli/subcommands/update.py` - `python -m keprix update`:
1. Check `https://api.github.com/repos/malike2356/keprix/releases/latest`
2. Compare with current version
3. If newer: download release tarball, apply to installation directory
4. Re-run `uv sync` and `pnpm install`
5. Restart services

For Docker installs: `docker compose pull && docker compose up -d`.
Auto-detect install method (Docker vs native) from presence of `/.dockerenv`.

Implement as a new `backend/cli/subcommands/update.py` module.

## Documentation

Create `keprix/docs/`:

`docs/01-self-host.md`:
- Quick start (docker compose)
- Manual install
- Reverse proxy setup (nginx, Caddy, Traefik examples)
- HTTPS with Certbot
- Systemd service (native install)

`docs/02-configuration.md`:
- Full `.env` reference (every variable with type, default, description)
- `config.yaml` reference

`docs/03-providers.md`:
- How to configure each of the 23 LLM providers
- Free options: Ollama (local), Groq (free tier), DeepSeek (cheap)
- Getting API keys for: OpenAI, Anthropic, DeepSeek, Gemini, Groq

`docs/04-channels.md`:
- Telegram bot setup (BotFather step-by-step)
- Discord bot setup
- Slack app setup
- WhatsApp (Baileys) setup
- Each in its own section with exact env var names

`docs/05-upgrade.md`:
- How to upgrade between versions
- Migration notes for breaking changes
- Backup before upgrade

`docs/06-carina-aiva.md`:
- What Aiva (commercial, separate product) (Enterprise) offers that keprix does not
- Aiva AI Employee workers and billing
- Labyrinth Scout full governance (vs Scout bridge in keprix)
- Blockchain trust and on-chain attestation
- Multi-tenant client management
- Link to carinaai.uk for Aiva (commercial, separate product) enquiries
- Link to labyrinthscout.com for Labyrinth Scout governance

`docs/07-sdk.md`:
- How to install the SDK:
  - Python: `pip install keprix-sdk`
  - Node.js: `npm install @keprix-ai/sdk`
- CarinaApp quickstart
- Schema registration example
- Full API reference for the Python SDK
- Full API reference for the TypeScript SDK

`docs/08-keprix-agent.md`:
- What the keprix Agent is and how it works
- How the approval workflow functions
- How to review and manage generated tools
- Security model for generated code

`docs/09-license.md`:
- keprix is MIT licensed in full
- What MIT means: anyone can use, modify, distribute, and build commercial products with
  no restrictions, as long as the copyright notice is preserved
- THIRD_PARTY_NOTICES.md explains legal compliance for incorporated code
- Verlox Limited makes no claim beyond what MIT requires

`docs/10-labyrinth-scout.md`:
- What Labyrinth Scout is and why you might want it
- How to enrol keprix with Labyrinth Scout (see Prompt 30)
- What the Scout bridge in keprix does and does not provide
- Link to labyrinthscout.com for pricing and full Scout capabilities

## Release Checklist

Create `keprix/RELEASE_CHECKLIST.md` (use the release checklist in this prompt):

### Foundation (Prompts 00-15)
- [ ] Directory tree matches architecture in Prompt 00
- [ ] `docker compose up` starts all 5 core services clean
- [ ] `GET /api/health` returns 200 within 100ms
- [ ] Agent chat (web UI + CLI) works with at least one provider
- [ ] Memory: save and search works
- [ ] Cron: create job, trigger run, receive delivery
- [ ] All 20+ messaging channels configured or stubbed
- [ ] Deep Research completes a run with citations
- [ ] Playbook: hardware scan and model fit scores
- [ ] Email: IMAP connect and AI summary of first email

### Security (Prompts 12, 21-29)
- [ ] Auth: login, logout, TOTP 2FA
- [ ] Vault: create item, unlock, retrieve, lock
- [ ] Backup: create .zip backup, restore it
- [ ] Cyber case creation and authorization system
- [ ] nmap scan on authorized target: output parsed, findings saved
- [ ] SIEM: syslog ingestion, Sigma rule fires, alert created
- [ ] AnonSurf: start, IP becomes Tor exit, stop, normal IP restored

### Platform Extensions (Prompts 17-20)
- [ ] SDK Python: CarinaApp connects, registers domain, parses NL command to ActionPlan
- [ ] SDK TypeScript: same test
- [ ] Builder: analyse a verlox project, returns StackReport
- [ ] Scout bridge: enrolls a test project, sends heartbeat

### keprix Agent (Prompt 28)
- [ ] Gap detector fires on an unknown task
- [ ] Tool synthesiser generates valid Python code
- [ ] Static analyser blocks eval() in generated code
- [ ] Sandbox runs with --network=none
- [ ] Approval card appears in web UI
- [ ] Approved tool installs live (no restart)
- [ ] Retried task succeeds with new tool

### Quality
- [ ] `pnpm build` in frontend succeeds
- [ ] `python -m keprix doctor` all PASS
- [ ] LICENSE contains "MIT License" and "Verlox Limited" and "keprix"
- [ ] THIRD_PARTY_NOTICES.md present (legal compliance only, not linked from UI)
- [ ] CLI banner: "keprix v1.0.0 - The keprix Agent"
- [ ] Web footer: "keprix - Community Edition"
- [ ] Zero matches for "Carina CE", "carina_ce", "carina-ce" in non-attribution files
- [ ] Mobile iOS build succeeds (xcodebuild)
- [ ] Mobile Android build succeeds (./gradlew assembleDebug)
- [ ] All 300+ tools visible in `GET /api/cyber/tools`

## Acceptance Criteria

- `grep -ri "openclaw\|hermes.agent\|odysseus" keprix/ --include="*.py" --include="*.ts" --include="*.tsx" --include="*.md"` returns zero matches outside of THIRD_PARTY_NOTICES.md
- `grep -ri "Carina CE\|carina_ce\|carina-ce\|CARINA_CE" keprix/ --include="*.py" --include="*.ts" --include="*.tsx" --include="*.md"` returns zero matches
- `cat keprix/LICENSE` contains "Verlox Limited" and "MIT License" and "keprix"
- No `LICENSE-AGPL.txt` or `ACKNOWLEDGMENTS.md` exists in the repository
- `THIRD_PARTY_NOTICES.md` exists and contains at least one copyright notice
- `docker compose config` in `keprix/` validates without error
- Footer in frontend shows "keprix - Community Edition"
- CLI banner shows "keprix v1.0.0 - The keprix Agent"
- `curl -fsSL http://localhost:3000` returns the launcher page HTML
- `pip install keprix-sdk` installs without error
- `npm install @keprix-ai/sdk` installs without error
