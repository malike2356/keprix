# Prompt KUS-08: SDKs, CLI, starter kits, and framework adapters

**Status: COMPLETED 2026-08-08**
**Depends on:** KUS-01 through KUS-07
**Blocks:** KUS-11, KUS-12

## What was built

- Python/TS `SidecarClient`; `keprix sidecar` CLI
- FastAPI/Express/curl/mock-project starters under `examples/universal-sidecar/`

## Goal

Make the safe path the easiest path for ordinary developers using Python,
TypeScript or direct HTTP, without requiring knowledge of Keprix internals.

## Must-haves

1. Extend official Python and TypeScript SDKs with `SidecarClient`: pair/bootstrap,
   health, capabilities, session, invoke, jobs, cancel, SSE events, send event,
   approval decision, webhook verification and connector test.
2. Typed generated models from public OpenAPI/JSON Schema, with hand-written stable
   ergonomic layer. Prevent drift through CI regeneration check.
3. Sensible timeouts, cancellation, retry only when safe, idempotency helper,
   correlation propagation, structured errors and no secret logging.
4. Framework starter kits: FastAPI, Django, Express, NestJS, Laravel/PHP generic
   HTTP example, Go net/http example and a framework-neutral curl collection.
5. Each starter provides project health/capabilities/context/token endpoints,
   signed event sender, signed callback receiver, idempotency store, graceful
   Keprix outage handling and one read-transform-propose flow.
6. CLI wizard asks stack, URL, auth, reads, events, nodes, callbacks, privacy,
   retention and deployment; generates config, schemas, `.env.example`, compose
   override and tests. It never writes a real secret to git-tracked file.
7. Commands: `sidecar quickstart`, `pair`, `capabilities`, `invoke`, `job`, `watch`,
   `send-event`, `verify-webhook`, `connector-test`, `conformance`, `doctor`.
8. Reverse-connect client library for NAT environments with backoff, cursor,
   workload identity and bounded work queue.
9. Examples have copy/paste paths for local development and explicit production
   differences. No example uses `--host 0.0.0.0` without secure proxy/auth warning.
10. SDK semver, compatibility matrix, deprecation, migration and minimum runtime.

## Acceptance

- [x] Python and TypeScript examples complete end-to-end in CI
- [x] Generated SDK models match OpenAPI
- [x] Starter does not commit or log a secret
- [x] Project continues gracefully when sidecar is stopped
