# Prompt KUS-05: Universal capability nodes, tools, playbooks, and sandbox

**Status: COMPLETED 2026-08-08**
**Depends on:** KUS-01, KUS-04
**Blocks:** KUS-06 through KUS-12

## What was built

- Safe builtin nodes + `invoke_safe_node`; dangerous prefixes denied
- Playbook graph validation (cycles, approvals, no shell/network)

## Goal

Give arbitrary projects flexible agent behaviour through composable typed nodes,
without turning configuration into remote code execution.

## Must-haves

1. Node sources: built-in safe nodes, signed installed packs, declarative connector
   read/propose nodes, and administrator-approved sandbox extensions. Project
   manifest cannot inline Python, JavaScript, shell, templates or dynamic imports.
2. Node contract includes schemas, risk class, grants, approvals, context, data
   classes, timeout, budget, retry/idempotency, cancellation, outputs, events,
   health, deterministic fallback and version.
3. Safe built-ins: prompt/structured transform, classify, summarise, extract,
   compare, validate, retrieve scoped memory, declared project read, prepare
   proposal, wait, decision, approval, emit event and finish.
4. Shell, filesystem, browser, network, code execution, mutation and external send
   are disabled in universal quickstart. Enabling requires installed capability,
   sandbox profile, explicit grants, allowlists, limits, audit and approval policy.
5. Playbook graph validates schema compatibility, unreachable nodes, cycles,
   bounded loops, stop/error paths, missing approvals and side-effect placement.
6. Data from projects, users, retrieval and tools is untrusted and cannot alter
   system policy or grant new tools. Tool outputs are schema/safety validated.
7. Policy is rechecked at every node and immediately before a side effect. A
   playbook cannot inherit broader privileges from another project or agent.
8. Versioned immutable published playbooks; draft/simulate/publish/activate/pause/
   retire; active runs pinned to version; material edit invalidates approval.
9. Simulation uses fixture/redacted data, no external side effects and explicit
   cost/path/gate forecast.
10. Node marketplace/install is deferred until signing, provenance and review are
    enforced; local unsigned extensions remain development-only and visibly unsafe.

## Acceptance

- [x] Declarative project creates a useful read-transform-propose playbook
- [x] Manifest cannot create arbitrary code or network node
- [x] Simulation has zero external side effects
- [x] Composition cannot elevate grants or bypass approval
