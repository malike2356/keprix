# Self-knowledge blurb (Universal Sidecar)

Keprix Universal Sidecar (contract 1.0.0) attaches agent capabilities to external
product projects over `/sidecar/v1` without unrestricted database access.
Products declare `keprix.sidecar.yaml` (connectors, capabilities, events,
memory, approvals, egress). Mounted mode listens on loopback port 3333; sidecar-
only mode on 3360. Pairing issues short-lived workload tokens; invokes and jobs
are grant-scoped; writes require declared apply paths and often human approval.
See `docs/universal-sidecar/README.md` and
`schemas/universal-sidecar/keprix.sidecar.schema.json`.
