# Keprix Universal Sidecar programme

**Status: COMPLETED 2026-08-08**
**Audience:** Any developer connecting any self-hosted application to Keprix
**Foundation:** `../keprix-sidecar-foundation/`
**Security contract:** `../ref-keprix-product-sidecar-contract.md`

## What was built

- Programme complete; see archived prompts and `docs/universal-sidecar/README.md`

## Outcome

A developer installs Keprix, runs a guided initializer, edits one declarative
project manifest, starts a private sidecar endpoint, completes pairing, and can:

- discover permitted capabilities;
- send bounded context and events;
- invoke safe synchronous nodes;
- start/cancel durable jobs and watch progress;
- receive signed result/action webhooks;
- let Keprix read only allowlisted project endpoints;
- review or approve proposed external actions;
- use official Python and TypeScript clients;
- run a conformance test before enabling production traffic.

No custom Keprix fork is required. Configuration cannot grant capabilities that
the installed pack/runtime does not provide, and cannot bypass policy or sandboxing.

## Build order

1. `00-architecture-public-contract-and-compatibility.md`
2. `01-project-manifest-schema-and-validation.md`
3. `02-sidecar-server-port-routes-and-transports.md` (archived 2026-08-08 under `prompts-archive/keprix-universal-sidecar/`)
4. `03-pairing-identity-authentication-and-grants.md`
5. `04-project-api-connectors-and-configured-access.md`
6. `05-capability-nodes-tools-playbooks-and-sandbox.md`
7. `06-events-jobs-webhooks-streaming-and-idempotency.md`
8. `07-context-memory-files-privacy-and-retention.md`
9. `08-sdks-cli-starter-kits-and-framework-adapters.md`
10. `09-operator-ui-observability-budgets-and-kill-switches.md`
11. `10-deployment-docker-compose-kubernetes-airgap-and-upgrades.md`
12. `11-security-conformance-fuzz-load-and-release-gates.md`
13. `12-documentation-examples-versioning-and-public-release.md`

## Port decision

- Mounted mode: existing Keprix backend, normally `127.0.0.1:3333`.
- Sidecar-only mode: proposed default `127.0.0.1:3360`, configurable through
  `KEPRIX_SIDECAR_HOST` and `KEPRIX_SIDECAR_PORT`.
- Production: private container/service network. Public binding requires explicit
  TLS/auth configuration and a security warning; anonymous invocation is forbidden.

## Definition of ready

One unmodified example application in each supported starter stack can initialise,
pair, discover, invoke, run a job, stream progress, receive a signed callback,
survive Keprix outage, rotate credentials and pass conformance using documentation
alone. Security and compatibility tests must cover existing product packs.
