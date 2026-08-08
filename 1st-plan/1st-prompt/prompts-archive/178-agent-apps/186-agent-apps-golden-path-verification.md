# Agent brief: Agent Apps golden path (Prompt 186)

## Status: VERIFIED (2026-07-12)

Automated smoke closed this brief (`tests/agent_apps/`: 116 passed). Live UI walkthrough remains an optional operator check on a running instance; it is not a pending build item.

## Goal

Verify the sellable Agent Apps product after prompts 178-186. Automated smoke is the archive gate; the checklist below is an optional live runbook.

## Automated smoke (archive gate)

```bash
cd /opt/lampp/htdocs/verlox/keprix
PYTHONPATH=src python3 -m pytest tests/agent_apps/ -q
PYTHONPATH=src python3 -m pytest tests/agent_apps/test_eval_suite_wiring.py -q
PYTHONPATH=src python3 -m pytest tests/agent_apps/test_scaffold_cli.py -q
```

**Result (2026-07-12):** 116 passed.

## Optional live runbook

### Hub and discover

1. Sign in and open `/agent-apps`.
2. First-visit intro tooltip appears; dismiss it and confirm it stays hidden on refresh.
3. **Discover** tab lists at least three templates (Daily Standup, Research Brief, Invoice Review).
4. `/launcher` shows an **Agent Apps** card; `/hub` shows **Open Agent Apps** link.

### Install and run

5. Install **Daily Standup** in one click; land on app detail.
6. Readiness is green, or set `KEPRIX_DEFAULT_PROVIDER` and refresh until ready.
7. Fill the focus field, click **Run**, see markdown output.
8. **History** tab shows the run with success status.

### Automate

9. Enable schedule **Weekdays 9am** on Pro plan (or confirm lock on Community).
10. Open `/admin/cron` and confirm a job with agent app source appears.
11. Rotate webhook; `curl` POST to public hook URL returns success.

### Lifecycle

12. **Export** bundle zip; uninstall app; reinstall from `/agent-apps/install` upload.
13. On Community plan, **Research Brief** install shows upgrade CTA (402).

### Evals, CLI, runtime

14. Run eval suite from app detail or `/evals` workflow `agent-apps`.
15. `keprix agent-app catalog list` and `keprix agent-app run ./path` succeed locally.
16. `/agent-runtime` lists agent app runs when filtered.
17. `bash scripts/serve-docs.sh`; open **Agent Apps** guide; links from docs index resolve.

## Pass criteria

- All automated tests green without live Stripe or external webhooks.
- No `TODO` or `coming soon` strings on `/agent-apps` routes.
- `/pricing` Agent Apps copy matches `config/agent_apps.yaml` limits.

## Related docs

- [docs/features/agent-apps.md](../../../../docs/features/agent-apps.md)
- Planning reference: `prompts-archive/ref-177-agent-apps-product-architecture.md`
