# Nodes and playbooks

## Capability nodes

Each node declares a stable key, version, sync/async execution, I/O schemas,
risk class, required grants, context slices, events, cost/timeout/retry policy,
and live/stub status.

Safe built-ins for quickstart include:

`prompt.transform`, `classify`, `summarise`, `extract`, `compare`, `validate`,
`memory.retrieve`, `project.read`, `proposal.prepare`, `wait`, `decision`,
`approval.request`, `event.emit`, `finish`.

Dangerous prefixes (`shell.`, `fs.`, `browser.`, `network.`, `code.`,
`mutate.`, `send.`, `exec.`) are disabled unless an installed pack + sandbox
explicitly allow them.

## Binding in the manifest

```yaml
capabilities:
  - node: summarise
    version: "1.0.0"
    scopes: [invoke:summarise]
    context_sources: [order.summary]
    timeout_seconds: 60
```

## Playbooks

Nodes compose into playbooks. A playbook **cannot** elevate caller grants or
bypass a node's approval, policy, budget, or product-side validation.

Invoke only advertised nodes via `POST .../invoke`. There is no generic
arbitrary tool executor.
