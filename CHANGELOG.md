# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- External human review gateway with tokenized public review pages.
- Legal acceptance gate with HTTP 451 middleware and `/legal/accept` UI.
- Browser action engine HTTP API with approval gates for risky actions.
- jamovi export bridge for analytics workspace workflows.
- Community infrastructure: issue templates, PR template, CI validation, and contributor docs.

### Changed

- Analytics workspace UI exports jamovi-ready dataset packages.
- Privacy centre UI adds retention policy editing and dry-run erasure preview.

## [0.1.0] - 2026-07-05

### Added

- Initial Keprix Community Edition release.
- FastAPI backend with workspace modules (documents, notes, tasks, calendar).
- Next.js frontend shell with contract-driven navigation.
- Agent tool registry, export pipeline, GDPR privacy centre, and research registry.
