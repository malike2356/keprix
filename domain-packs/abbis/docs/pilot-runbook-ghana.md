# ABBIS Ghana pilot runbook

**Status:** READY FOR STAGING PILOT (capped)
**Operator:** Ghanaian operating company (not VERLOX)
**Association:** Borehole Drillers Association of Ghana (BDAG)

## Pilot scope

- Tenants: max 3 rig-owner orgs + optional BDAG exec observer
- Languages: English + Twi (Hausa optional)
- Channels: web + one configured messenger (WhatsApp or Telegram)
- Nodes enabled: field calculators, job brief, drilling log propose, quote calculate
- National aggregate: off unless BDAG explicitly activates

## Support

- Product support owns user identity and entitlements
- Keprix sidecar support owns agent/session/queue health only
- Stop thresholds: isolation failure, formula mismatch, duplicate finance post, cross-tenant RAG hit

## Rollback

1. Disable sidecar feature flag in ABBIS
2. Drain AI queue without replaying stale authority
3. `POST /v1/products/abbis/rollback` with last-known-good pack version
4. Confirm product core health and calculators still local

## Data processing

- Purpose-limited context slices only
- No raw worker/client dumps in channel messages
- Retention per pack policies; deletion events must clear sidecar memory indexes
