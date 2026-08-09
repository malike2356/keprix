# Install and startup troubleshooting

## Symptom: UI up but API health fails

**Fix:**

```bash
curl -s http://127.0.0.1:3333/api/health
docker compose -f docker/docker-compose.yml ps
```

Restart backend if unhealthy. Confirm `.env` has at least one LLM provider key for chat.

## Symptom: Fresh install; chat cannot answer

**Fix:** Complete [First run](../getting-started/first-run.md). Add an LLM key. Optionally run `keprix memory index-self` so the agent knows Keprix product facts ([Self-knowledge](self-knowledge.md)).

## Symptom: Wrong ports on Contabo

Public app is `https://app.keprixai.com`. Host loopback for sidecars is often `127.0.0.1:13333`. See [keprixai.com origin](../operations/keprixai-com-origin.md).

## Related

- [Install](../getting-started/install.md)
- [Quickstart](../getting-started/quickstart.md)
- [Environment variables](../configuration/environment-variables.md)
