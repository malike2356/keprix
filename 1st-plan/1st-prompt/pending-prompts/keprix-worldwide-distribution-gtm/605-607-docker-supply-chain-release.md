# Prompts 605-607: Docker, supply chain, and releases

**Status:** PENDING
**Depends on:** 600-602

## Prompt 605: public multi-architecture Docker delivery

Build and publish backend and frontend OCI images for linux/amd64 and linux/arm64
under a verified Keprix namespace. Use buildx, pinned base image digests, minimal
runtime images, non-root users, health checks, OCI labels, read-only filesystem
where compatible, dropped capabilities, resource guidance, and version plus digest
pinning. Remove `continue-on-error` from release publication and fail if registry
credentials or pushes fail.

Provide a public Compose quickstart that pulls release images by version or digest,
plus a contributor overlay that builds locally. Generate secrets with safe file
permissions, never ship default passwords, bind databases privately, and document
reverse proxy and TLS. Add fresh install, restart, upgrade, backup, restore,
rollback, arm64, amd64, volume ownership, health, and sidecar profile tests.

## Prompt 606: artifact integrity and software supply chain

Produce SHA-256 files, CycloneDX or SPDX SBOMs, dependency and licence reports,
SLSA-compatible provenance, and keyless Sigstore signatures for every release
artifact and image. Add secret scanning, dependency review, CodeQL, container
scanning, malicious package checks, and release attestation verification. Pin GitHub
Actions by commit or an approved policy. Document verification commands for users.

Fail stable publication on critical vulnerabilities unless an approved, expiring
exception documents exploitability, mitigation, owner, and deadline. Do not print
credentials or upload environment files in artifacts.

## Prompt 607: GitHub Release factory

Create a protected release workflow that runs the full quality matrix, builds each
artifact once, signs it, publishes a draft GitHub Release, validates every download
from an anonymous context, then promotes the exact same bits. Attach manifest,
checksums, SBOMs, provenance, source archives, CLI packages, and desktop packages.
Publish Docker and PyPI only after their gates pass. Never mark the overall job green
when required publication was skipped or failed.

Add release concurrency, environment approvals, tag protection, changelog generation,
rollback notes, release notes with known issues, and a post-publish audit. Test the
workflow with a prerelease channel before stable.
