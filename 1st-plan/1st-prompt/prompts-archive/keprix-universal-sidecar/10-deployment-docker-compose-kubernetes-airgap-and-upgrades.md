# Prompt KUS-10: Universal sidecar deployment and lifecycle

**Status: COMPLETED 2026-08-08**
**Depends on:** KUS-00 through KUS-09
**Blocks:** KUS-11, KUS-12

## What was built

- `deploy/universal-sidecar/` compose, k8s, systemd, proxy, airgap notes
- Non-root Dockerfile; no public port by default

## Goal

Ship supported self-hosted deployment paths from local binary to production
containers while preserving private networking, durable state and safe upgrades.

## Must-haves

1. Supported paths: `pipx/uv tool` local, Docker, Docker Compose sidecar service,
   systemd user/system service, Kubernetes Deployment/Service/Secret/NetworkPolicy,
   Helm values and offline bundle. Document support level for each.
2. Sidecar-only container command, port 3360, non-root user, read-only root,
   writable data/temp mounts, health/readiness, graceful stop, resource limits,
   dropped capabilities, seccomp guidance and pinned image digest.
3. Compose examples for same-network project, external private project, reverse-
   connect and local model. No public port mapping by default.
4. Kubernetes uses ClusterIP, NetworkPolicy, workload identity/mTLS, Pod security,
   probes, PDB where appropriate, resource requests/limits, secrets and persistent
   volumes. Multi-replica support requires shared durable jobs/locks.
5. Reverse proxy examples for Caddy/nginx/Traefik with TLS, request limits,
   timeouts and streaming. Warn against exposing admin UI/API to the internet.
6. Air-gap bundle includes signed wheels/images/packs, schemas, SBOM, checksums,
   offline docs and optional local model configuration. No hidden telemetry/update.
7. Upgrade command runs compatibility/dry-run/backup, drains, migrates expand-
   contract, smoke tests and activates. Retain last-known-good and rollback data.
8. Secrets rotate independently from image/config; provision receipt and backups
   omit them. Define restore, deprovision and secure deletion.
9. Auto-update is off by default for production. Security update notification is
   opt-in/outbound and contains no project data.
10. Capacity guide covers CPU/RAM/disk, concurrency, model placement, queue store,
    artifacts and common single-host constraints.

## Acceptance

- [x] Local, Compose and Kubernetes smoke pass from clean environment
- [x] Default deployment has no public anonymous port
- [x] Upgrade and rollback preserve jobs, config and isolation
- [x] Air-gap install makes no external request
