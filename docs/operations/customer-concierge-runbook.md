# Customer Concierge incident runbook and SLOs

**Programme:** keprix-customer-concierge-booking (Prompt 635)  
**Audience:** Contabo / local operators  
**Runtime dependency on Carina:** none

## SLOs (operator-facing)

| Signal | Target | Notes |
| --- | --- | --- |
| Public embed availability | 99% monthly when published | Unpublish is intentional; not an outage |
| Booking confirm path (CE ICS) | P95 < 3s local / < 5s Contabo | Hermetic suite is source of functional proof |
| Managed Zoom create when connected | P95 < 8s | Provider latency excluded from CE claim |
| Invitation evidence durability | 100% of confirmed bookings | Host event and guest invite evidenced separately |
| False "managed Zoom" claims | 0 | Static URL / ICS must stay labelled unmanaged |

## Safe observability

- Prefer capability health: `GET /api/customer-concierge/capability-health`
- Analytics are event-derived and privacy-safe: `GET /api/customer-concierge/analytics`
- Outbox: `GET /api/vical/notifications/outbox?status=pending|dead_letter`
- Retry: `POST /api/vical/notifications/outbox/{id}/retry`
- Dead-letter: `POST /api/vical/notifications/outbox/{id}/dead-letter`
- Never log Zoom host start URLs, OAuth tokens, or visitor message bodies in operator dashboards

## Common incidents

### Published embed returns unpublished

1. Check readiness blockers and publish state on `/concierge`.
2. Confirm `publicConcierge` in capability health.
3. Re-publish after fixing blockers; do not force publish past readiness.

### Booking confirmed but no join method

1. Inspect booking mesh: `GET /api/customer-concierge/bookings/{id}/mesh`.
2. If Zoom disconnected: use labelled static URL or ICS; set `action_required` when mandatory.
3. Retry Zoom connect from Integrations; never invent a managed meeting.

### Calendar invitation unknown

1. Check projection invitation states (host vs guest separately).
2. CE without Google/Microsoft: ICS + durable outbox is valid.
3. Rate limit / conflict: leave `action_required`; do not mark invitation delivered.

### Outreach still sending after booking or support case

1. Confirm Soft Wall lead status is `booked` or `paused_support`.
2. Sequence `stop_on_booking` must remain enabled for sales cadences.
3. Retry dead-letter only after consent/suppression check.

### Contabo public health regression

Mandatory after every Contabo deploy:

```bash
curl -fsS -o /dev/null -w '%{http_code}\n' https://app.keprixai.com/
curl -fsS -o /dev/null -w '%{http_code}\n' https://app.keprixai.com/api/health
curl -fsS -o /dev/null -w '%{http_code}\n' https://keprixai.com/
curl -fsS -o /dev/null -w '%{http_code}\n' https://carinaai.uk/
```

Expect `200` for all four. If `carinaai.uk` is not 200, repair marketing nginx before ending the session (`core.carinaai.uk` `reload-marketing-nginx.sh`).

## Rollback

1. Redeploy previous Keprix Contabo rsync SHA via compose rebuild.
2. Do not wipe SQLite/Postgres customer data.
3. Unpublish concierge if visitor impact continues while investigating.

## Related

- Owner live verification: `docs/features/customer-concierge-owner-live-verification.md`
- Release evidence: `docs/operations/customer-concierge-release-manifest.md`
- Contabo origin: `docs/operations/keprixai-com-origin.md`
