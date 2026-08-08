# Prompt 418 / 02: Public git hygiene

**Status: COMPLETED 2026-08-07**  
Series: Keprix public GTM + Hermes install parity  
Depends on: 417  
Blocks: 419, 421  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Purpose

Make the git tree safe to publish: ignore rules, export-ignore for workspace
planning, clean root story, and an explicit owner checklist to flip the GitHub
repo to public.

## Tasks

1. Harden `.gitignore` (confirm or add):
   - `.env`, `.env.*`, `!.env.example`
   - `keprix-data/`, `.venv/`, `frontend/node_modules/`, `**/node_modules/`
   - `.pytest-data/`, coverage, `.next/`, `site/` build output if generated
   - local Stripe/credential filenames if any ever appeared under the tree
2. Add `.gitattributes` `export-ignore` (and document in CONTRIBUTING) for
   paths that must not appear in source archives / release tarballs:
   - `1st-plan/`
   - optional: `AGENTS.md`, `CLAUDE.md` if they encode Verlox-only ops
   - Confirm product `docs/`, `src/`, `frontend/`, `docker/` are **not** ignored.
3. Root layout hygiene for first-time cloners:
   - README is the only required entry doc at root.
   - Multiple root `docker-compose*.yml` / `fly*.toml`: either keep with a short
     `deploy/README.md` pointer, or move non-primary compose under `docker/` /
     `deploy/` with redirects in docs. Do not break existing scripts.
4. Owner checklist file: `docs/operations/public-github-checklist.md`
   - Flip repo visibility to public (or create public mirror and update URLs).
   - Verify anonymous: `curl -fsSIL https://github.com/malike2356/keprix`
   - Verify raw: `curl -fsSIL https://raw.githubusercontent.com/malike2356/keprix/main/README.md`
   - Branch protection / secrets scan notes (no secret values in doc).
5. Do not force-push. Do not rewrite history unless owner explicitly asks.

## Acceptance

- [x] `.gitattributes` export-ignores `1st-plan/`.
- [x] Public GitHub checklist exists and is linked from sign-off (428).
- [x] No secrets staged.
- [x] Primary Compose path remains `docker/docker-compose.yml`.

## Verification

```bash
rg -n 'export-ignore' .gitattributes
rg -n '1st-plan' .gitattributes
test -s docs/operations/public-github-checklist.md
# Soft check: anonymous reachability (may fail until owner flips visibility)
curl -fsSIL -o /dev/null -w '%{http_code}\n' https://github.com/malike2356/keprix || true
```


## What was built

- Hardened `.gitignore` secrets section (`.env.*`, credentials, Stripe secret patterns, Graphiti env).
- Created `.gitattributes` with `export-ignore` for `1st-plan/`, `AGENTS.md`, `CLAUDE.md`.
- Added `deploy/README.md` (Compose / Fly pointers; no file moves).
- Added owner checklist `docs/operations/public-github-checklist.md`.
- Linked checklist from CONTRIBUTING.md and sign-off prompt 428.
- Updated public GTM gap map (418 DONE; GitHub anonymous OPEN until owner flip).

## Owner gate

Making the repository public is an **owner action**. Implementation may prepare
everything else; 426/428 must fail closed while anonymous GitHub is 404.
