# Agent OS Phase 5 polish

Stub for Phase 5 polish: ship defaults on `/agent-os/glass`, playbook/guardrails CLI, and error-paste workflow.

```bash
keprix agent-os playbook
keprix agent-os guardrails
keprix agent-os workflow error-paste --error "ModuleNotFoundError: No module named foo"
```

Production deploy pointer:

```bash
bash scripts/deploy-keprix-production.sh --bootstrap --domain app.example.com --skip-scout
```

## Related

- [Agent OS overview](agent-os-overview.md)
- [Phase 4 workflows](agent-os-phase4-workflows.md)
- [VPS deploy](../operations/vps-deploy.md)
- [Playbooks](playbooks.md)
