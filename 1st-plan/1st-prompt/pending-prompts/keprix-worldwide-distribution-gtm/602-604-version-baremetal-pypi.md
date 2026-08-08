# Prompts 602-604: versioning, bare metal, and PyPI

**Status:** IN PROGRESS (602 completed 2026-08-08; 603-604 pending)
**Depends on:** 600-601

## Prompt 602: canonical version and manifest

Implement a single version source and automated synchronization for Python,
desktop, Docker labels, API responses, TUI, website, and release notes. Reject a
release when any component differs. Generate and validate the release manifest
defined in 601. Add migration compatibility metadata and a machine-readable
`keprix version --json` response that contains no secrets.

Tests: dirty-tree behavior, prerelease versions, tag mismatch, component mismatch,
manifest schema, deterministic ordering, and rollback compatibility.

**Prompt 602 status: COMPLETED 2026-08-08.** Added canonical version enforcement,
release manifest validation and integrity records, CI drift rejection, synchronized
desktop version, ISO release date, `keprix version --json`, and focused tests.

## Prompt 603: stranger-safe bare-metal installer

Replace development-oriented public installation with a stable path. The default
installer must resolve an immutable stable tag, verify the downloaded manifest and
SHA-256 before execution or installation, create an isolated environment, avoid an
editable `main` checkout, and never require root. Preserve an explicit developer
checkout mode. Add `--channel`, `--version`, `--prefix`, `--non-interactive`,
`--dry-run`, `--doctor`, `--uninstall`, and safe repair behavior.

Support the matrix from 601 only. Detect Python, disk, architecture, libc, ports,
filesystem permissions, PATH, proxies, and required tools. Fail with actionable
copy and no partial destructive state. Make installation idempotent and preserve
user data on reinstall. Test filenames with spaces, non-English locales, offline
failure, interrupted download, bad signature, corrupt archive, occupied ports,
existing installs, and least-privilege users in clean VMs.

Do not use `curl | bash` as the only documented route. Offer download, inspect,
verify, then run. If the one-liner remains, state its trust model.

## Prompt 604: PyPI and pipx trusted publishing

Prepare and, only with explicit owner approval, publish the `keprix` distribution
through PyPI trusted publishing. Build wheel and sdist in isolated CI; validate
metadata, licence, package data, imports, entry points, dependency bounds, and
Python 3.11 and 3.12. Test installation from the built wheel with network-isolated
runtime smoke where practical. Publish to TestPyPI first, then PyPI from a protected
tag environment. Never use a long-lived PyPI token when OIDC is available.

After successful publication, update docs from pinned Git URLs to `pipx install
'keprix[tui]'`, while retaining a version-pinned fallback. The public gate must
query PyPI and verify that the documented version exists. If owner approval is not
available, leave publication blocked and keep docs honest.
