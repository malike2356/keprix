# Prompt 422 / 06: README + CONTRIBUTING install-first rewrite

**Status: COMPLETED 2026-08-07**  
Series: Keprix public GTM + Hermes install parity  
Depends on: 419, 421  
Blocks: 423  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Purpose

Rewrite the public front door so Keprix presents like Hermes: install first,
product story second, contributor path last. Remove workspace-internal framing.

## Tasks

1. Rewrite root `README.md`:
   - Badges (CI, license, release) only if URLs resolve for anonymous users
     after publicize; otherwise keep MIT badge and note CI after public.
   - Short product pitch (self-hosted agent OS, mutation with approval, MIT).
   - **Quick Install** section with curl one-liner (primary).
   - After install: `source` shell rc hint, `keprix setup`, `keprix tui`.
   - **Full stack (Docker)** secondary section.
   - Links: docs site / MkDocs, SECURITY, LICENSE, CONTRIBUTING.
   - Remove leading "Path: `/opt/lampp/htdocs/verlox/keprix`" from the public
     README (move to AGENTS.md / workspace notes only).
   - Repository layout table: product paths only; do not advertise `1st-plan/`
     as something users need.
2. Rewrite or trim `CONTRIBUTING.md` for external contributors:
   - Fork/clone, venv or `uv`, test commands, PR expectations.
   - Point to `docs/community/contributing.md` for depth.
3. Ensure LICENSE MIT text remains accurate; link Community Edition rules if any
   from private sign-off still apply.
4. Match marketing clone snippets to README (complete https URL).

## Acceptance

- [x] README opens with install within the first screen of content.
- [x] No Verlox absolute paths in README.
- [x] CONTRIBUTING is usable by a stranger.
- [x] Curl one-liner identical to `scripts/install-curl.sh` / docs.

## What was built

- Hermes-style root `README.md`: pitch, Quick Install (curl one-liner), post-install
  commands, Docker secondary path, shorter component table, product-only layout,
  docs links, CONTRIBUTING/Licence/Contact; related products link only.
- Trimmed `CONTRIBUTING.md` for fork/clone strangers; depth points to
  `docs/community/contributing.md`; kept public releases / export-ignore note.
- Spot-checked marketing HowItWorks curl + Compose (already correct from 420).
- Gap map + series README marked 422 DONE.

## Verification

```bash
rg -n 'curl -fsSL' README.md
rg -n '/opt/lampp/htdocs' README.md && exit 1 || exit 0
rg -n '1st-plan' README.md && exit 1 || exit 0
head -n 60 README.md
```
