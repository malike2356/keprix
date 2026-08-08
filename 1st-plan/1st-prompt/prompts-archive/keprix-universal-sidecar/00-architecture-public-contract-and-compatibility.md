# Prompt KUS-00: Universal sidecar architecture and public contract

**Status: COMPLETED 2026-08-08**
**Depends on:** existing public API, sidecar foundation, shared contract
**Blocks:** KUS-01 through KUS-12

## What was built

- `src/keprix/universal_sidecar/contract.py` ADR, modes, ownership, non-goals, pack migration map
- Contract name/version keprix-universal-sidecar 1.0.0; `/sidecar/v1` separated from OpenAI `/v1/chat`

## Goal

Define a stable public sidecar architecture for arbitrary projects without
breaking the OpenAI-compatible API, existing product packs or personal-agent mode.

## Must-haves

1. Publish architecture decision record covering personal OS, mounted sidecar,
   sidecar-only process, dedicated per-project deployment and hard-isolated shared
   runtime. State when each mode is safe and supported.
2. Ownership boundary: integrating project owns users, tenancy, entitlements,
   business records, UI and side effects. Keprix owns agent execution, configured
   capabilities, memory, jobs, policy, approvals and audit.
3. Define public contract name/version and additive compatibility policy. Separate
   Universal Sidecar endpoints from OpenAI-compatible `/v1/chat/*` and broad tools.
4. Define project, deployment, environment, tenant, actor, session, subject,
   capability, run, job, approval, event and artifact identifiers.
5. Define data-flow and threat models for local same-host, Docker network, remote
   private network, reverse-connect and optional air-gap deployment.
6. Define configuration trust: manifest requests capabilities, but installed
   runtime policy is the upper bound. A manifest cannot enable shell/network/file,
   mutation, browser, code execution or outbound side effects by naming them.
7. Define graceful degradation and project independence during Keprix outage.
8. Map existing five product pack contracts onto the universal contract and list
   compatibility adapters/migrations. Do not fork their runtime.
9. Decide supported baseline versions for Python, Node, Docker, SQLite/Postgres,
   OpenAPI, JSON Schema, CloudEvents and transport protocols.
10. Publish non-goals: arbitrary DB introspection, UI scraping, anonymous public
    agent endpoint, unrestricted tool proxy, automatic write authority and secret
    values in project manifests.

## Acceptance

- [x] Architecture covers trust, ownership, versions and every deployment mode
- [x] Existing personal-agent and OpenAI API contracts remain compatible
- [x] Universal configuration is request, never authority
- [x] Existing product packs have a documented migration path
