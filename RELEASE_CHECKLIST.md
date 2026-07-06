# Keprix release checklist

Use before merging a release-please PR or cutting a community edition release.

## Release automation

1. Conventional commits land on `main` (commitlint on PRs).
2. [release-please](https://github.com/googleapis/release-please) opens or updates a release PR
   with `CHANGELOG.md` and `pyproject.toml` version bumps.
3. Review the release PR changelog text; compare with `bash scripts/changelog-preview.sh` if needed.
4. Merge the release PR; release-please creates tag `vX.Y.Z` and a GitHub Release.
5. `.github/workflows/release.yml` runs backend tests, frontend build, and Docker publish on
   `release: published`.

Manual steps you no longer need:

- Moving `## [Unreleased]` bullets into a versioned section by hand.
- Pushing a tag manually for routine releases.
- Running `awk` to extract release notes (release-please writes the GitHub Release body).

## Brand and legal

- [ ] `LICENSE` contains "MIT License", "Verlox Limited", and "keprix"
- [ ] `THIRD_PARTY_NOTICES.md` present (not linked from UI)
- [ ] No `LICENSE-AGPL.txt` in the repository
- [ ] Workspace UI footer shows "keprix - Community Edition"
- [ ] CLI startup banner shows community edition lines
- [ ] `rg -ri "openclaw|hermes.agent|odysseus" frontend/src/app/\(workspace\)` returns zero matches
- [ ] `rg -ri "Carina CE|carina_ce|carina-ce" frontend/src` returns zero matches

## Build and health

- [ ] `cd frontend && pnpm build` succeeds
- [ ] `.venv/bin/python -m pytest tests/productization/ -q` passes
- [ ] `GET /api/health` returns 200
- [ ] `docker compose -f docker/docker-compose.yml config` validates

## Core workflows

- [ ] Agent chat works with at least one provider
- [ ] Vault create and retrieve works
- [ ] Support diagnostics bundle redacts secrets
- [ ] Scout bridge connects when configured (optional)
- [ ] Hub pack install and rollback works

## Install and upgrade

- [ ] `bash scripts/install.sh` completes on a clean machine
- [ ] `keprix update --check` reports version state
- [ ] `docs/05-upgrade.md` reviewed for breaking changes

## Documentation

- [ ] `docs/01-self-host.md` through `docs/10-labyrinth-scout.md` present
- [ ] `.env.example` documents `KEPRIX_TELEMETRY=false` default
