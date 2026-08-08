# Universal Sidecar deploy support levels

| Method | Support | Notes |
| --- | --- | --- |
| **pipx** | Community | `pipx install keprix` then `python -m keprix.universal_sidecar.app` |
| **Docker** | Supported | See `compose/Dockerfile.sidecar` |
| **Compose** | Supported | `compose/docker-compose.yml` (loopback-only comment; no public map by default) |
| **Kubernetes** | Supported | ClusterIP + NetworkPolicy under `kubernetes/` |
| **Helm** | Best-effort | Chart not shipped yet; use raw manifests as base |
| **Air-gap** | Supported | Offline bundle notes in `airgap/README.md` (no telemetry) |
| **systemd** | Supported | `systemd/keprix-sidecar.service` |
| **Proxy snippets** | Reference | Caddy / nginx / Traefik with TLS warnings |

Preferred production: dedicated sidecar per product deployment on a private
network. Never expose anonymous invoke publicly.
