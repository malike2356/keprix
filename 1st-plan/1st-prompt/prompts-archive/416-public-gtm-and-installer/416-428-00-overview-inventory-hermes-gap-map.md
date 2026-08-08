# Prompt 416 / 00: Overview, inventory, Hermes gap map

**Status: COMPLETED 2026-08-07**  
Series: Keprix public GTM + Hermes install parity  
Depends on: none  
Blocks: 417-428  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Agents must not guess what "clean for GTM" means. Capture a dated inventory of
workspace noise vs product, and a Hermes install UX gap map, before moving files
or rewriting installers.

## Goal

1. Produce `docs/architecture/public-gtm-gap-map.md` (or under `1st-plan/` if
   docs must stay product-clean until 425; prefer `docs/architecture/` once
   content is ship-safe).
2. Map each gap to OPEN / PARTIAL / DONE with absolute paths.
3. Point to this programme README and `ref-416-keprix-public-gtm-hermes-install-build-order.md`.

## Must-haves

### A. Product vs workspace inventory

Classify each top-level path under `/opt/lampp/htdocs/verlox/keprix/`:

| Class | Meaning |
| --- | --- |
| PRODUCT | Required for strangers who clone/run Keprix |
| DOCS | Public documentation / legal / community |
| TOOLING | CI, scripts, deploy helpers that belong in public repo |
| WORKSPACE | Verlox planning, local data, internal only |
| UNCLEAR | Needs owner decision in the gap map |

At minimum classify: `src/`, `frontend/`, `docker/`, `docs/`, `tests/`,
`scripts/`, `config/`, `migrations/`, `domain-packs/`, `evals/`, `examples/`,
`ui/`, `mobile/`, `sdk/`, `keprix_sdk/`, `packages/`, `apps/`, `apps-on-keprix/`,
`marketing/`, `site/`, `1st-plan/`, `keprix-data/`, `keprix-proxy/`, `deploy/`,
root `docker-compose*.yml`, `fly*.toml`, `AGENTS.md`, `CLAUDE.md`.

### B. Hermes install UX gap map

Compare against Hermes public UX (not TUI pixel parity):

| Hermes UX | Keprix today | Gap |
| --- | --- | --- |
| Public GitHub | anonymous 404 | OPEN |
| `curl …/install.sh \| bash` | raw URL 404; script assumes checkout | OPEN |
| Clone under `~/.hermes/hermes-agent` | mixed `~/keprix` + contributor `.venv` | OPEN |
| Binary on PATH (`hermes`) | pipx/docs claim PyPI missing | OPEN |
| `hermes setup` / chat next | wizard exists but not lead UX | PARTIAL |
| Docker full stack | Compose works locally with SSH clone | PARTIAL |
| Install-first README | clone+Compose; workspace path in README | OPEN |
| Public product domain | DNS for keprixai.com set; origin 520 | OPEN |

### C. Domain and copy facts

Record:

- Owner public domain: `keprixai.com` (not `keprixai.uk`).
- Cloudflare A records already point Contabo `80.190.81.208` (proxied).
- Origin lacks nginx vhost / Keprix containers (520). Frontend is separable
  from backend for marketing-only origin.

## Acceptance

- [x] Gap map file exists with dated status table.
- [x] Every OPEN row names the prompt ID that closes it (417-428).
- [x] Series README progress checkbox for 00 can be ticked.
- [x] Implementing agent can start 417 without re-scanning the whole tree.

## Verification

```bash
test -s docs/architecture/public-gtm-gap-map.md || test -s 1st-plan/1st-prompt/pending-prompts/keprix-public-gtm/GAP-MAP.md
rg -n 'keprixai\\.com|OPEN|WORKSPACE|PRODUCT' docs/architecture/public-gtm-gap-map.md 1st-plan/1st-prompt/pending-prompts/keprix-public-gtm/GAP-MAP.md 2>/dev/null
```

## What was built

- `docs/architecture/public-gtm-gap-map.md` with dated inventory + Hermes UX status table.
- Every OPEN/PARTIAL row maps to prompt IDs 417-428.
- Series README progress 00 ticked.

## Out of scope

- Moving files (417).
- Making the GitHub repo public (owner action noted in 418/428).
