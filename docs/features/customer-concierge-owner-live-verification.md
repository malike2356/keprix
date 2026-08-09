# Customer Concierge owner live provider verification

**Prompt 635**  
**Audience:** product owner  
**Rule:** do not paste secrets into chat, docs, commits, or tickets. Use env **names** only; values live in `.access/` or Contabo `.env`.

## Purpose

Hermetic tests prove CE behaviour with fakes. This guide is the optional owner-run checklist against real Zoom / Google / SMTP after CE is green.

## Preconditions

- Local or Contabo Keprix healthy (`/api/health` 200)
- Concierge published for a test persona
- Owner can access Integrations and `/concierge`

## Environment names (no values)

| Provider | Env names |
| --- | --- |
| Zoom OAuth | `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET`, `KEPRIX_CONCIERGE_ZOOM_WEBHOOK_SECRET` |
| Google Calendar | `GOOGLE_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, optional `KEPRIX_GOOGLE_CALENDAR_ACCESS_TOKEN`, `KEPRIX_CONCIERGE_GOOGLE_CALENDAR_WEBHOOK_TOKEN` |
| Microsoft Graph (optional) | `MICROSOFT_OAUTH_CLIENT_ID`, `MICROSOFT_OAUTH_CLIENT_SECRET` |
| Email transport (optional) | `SMTP_URL` or `SENDGRID_API_KEY` / `MAILGUN_API_KEY`, `KEPRIX_OUTREACH_FROM_EMAIL` |

## Checklist

1. Capability health shows honest `not_configured` / `disconnected` before connect.
2. Connect Zoom from Integrations; test connection succeeds; host start URL never appears in browser network payloads.
3. Create a real booking for a throwaway guest; confirm join URL present when Zoom connected.
4. Confirm host calendar event + guest invitation evidence separately (`/api/vical/bookings/{id}/invitation`).
5. Accept/decline from guest calendar; reconcile shows accepted / declined / tentative / unknown.
6. Reschedule and cancel; Zoom meeting and calendar update/delete; outreach cadence stays stopped.
7. Open support case; confirm Soft Wall lead pauses when matched.
8. Analytics refresh shows counts without message bodies.
9. Revoke Zoom; next booking must not claim managed Zoom (ICS / static fallback only).

## Pass criteria

- No fake success when a provider is disconnected
- No Carina or Aiva runtime call required
- Contabo public health still 200 including `https://carinaai.uk/`

## Fail / stop

Stop and keep CE mode if any live provider returns unexpected auth errors. Capture provider error **codes** only (not tokens) in the incident note.
