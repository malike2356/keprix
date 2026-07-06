# Notifications

In-app inbox, digests, push hooks, and external SMTP delivery.

## Web inbox (`/notifications`)

- Approval requests, mutation alerts, pack gate pending installs
- Mark read, filter by channel
- Escalation when approvals sit too long (configurable)

## Preferences (`/settings/notifications`)

| Setting | Purpose |
| --- | --- |
| Delivery channels | In-app, email, push toggles |
| Quiet hours | Suppress non-urgent alerts |
| Digest email | Summary when quiet hours end |
| Approval escalation | Remind approvers after N hours |

## External SMTP (`/settings/notifications/external`)

Admin-only SMTP for emails to **external** reviewers and compliance contacts. Separate from [Email](email.md) IMAP inbox accounts.

Fields: host, port, username, password (vault), from name/email.

Test: `POST /api/notify-external/test-email`

## API

- `/api/notifications/*` preferences and inbox
- `/api/notify-external/*` external delivery

## Related

- [Email](email.md)
- [Review gateway](../security/review-gateway.md)
- [Cron jobs](cron-jobs.md)
