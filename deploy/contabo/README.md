# Contabo marketing origin helpers

Runbook: [`docs/operations/keprixai-com-origin.md`](../../docs/operations/keprixai-com-origin.md)

| File | Role |
| --- | --- |
| `docker-compose.marketing.yml` | Marketing-only `keprix-frontend` on shared `proxy` network |
| Canonical nginx vhost | `carina/02-backends/core.carinaai.uk/docker/nginx/keprixai.com.conf` |

Do not install Caddy on Contabo 80/443. After any Contabo change, verify
`https://carinaai.uk/` returns HTTP 200.
