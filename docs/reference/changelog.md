# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Private ship readiness targets package version **0.16.0** (`pyproject.toml`).

### Added

- External human review gateway with tokenized public review pages.
- Legal acceptance gate with HTTP 451 middleware and `/legal/accept` UI.
- Browser action engine HTTP API with approval gates for risky actions.
- jamovi export bridge for analytics workspace workflows.
- Community infrastructure: issue templates, PR template, CI validation, and contributor docs.

### Changed

- Analytics workspace UI exports jamovi-ready dataset packages.
- Privacy centre UI adds retention policy editing and dry-run erasure preview.

## [0.16.0]

Ship-hardening sync for private deploy (no backdated feature diary). Package version is authoritative in `pyproject.toml`.

### Added

- Ops docs for Compose + Caddy VPS deploy and readiness (`docs/operations/vps-deploy.md`, `docs/operations/readiness.md`).
- Short stubs for previously empty MkDocs feature/security/frontend pages (brain, a2a, quotas, release signing, theme contrast, Agent OS phases, and related pointers).
- `AUTH_ENABLED` (default on) and `KEPRIX_MULTI_USER` (default off) documented in `.env.example`.

### Changed

- Environment variable reference descriptions repaired where comment parsing had leaked placeholder admin password text into Description cells.

## [0.1.0] - 2026-07-05

### Added

- Initial Keprix Community Edition release.
- FastAPI backend with workspace modules (documents, notes, tasks, calendar).
- Next.js frontend shell with contract-driven navigation.
- Agent tool registry, export pipeline, GDPR privacy centre, and research registry.
