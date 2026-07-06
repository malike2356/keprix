# Review gateway

External reviewers approve content without full workspace accounts.

## Web UI (`/review-gateway`)

- Create review requests with reviewer email
- Generate time-limited public tokens
- Track approve / reject / comment status

## Flow

1. Operator submits artifact (document, pack change, mutation)
2. Reviewer receives email with secure link (when SMTP configured)
3. Reviewer acts via token URL without logging in
4. Decision recorded in audit log

## API

Routes under `/api/review-gateway/*`. See [API reference](../reference/api.md).

## SMTP

Configure outbound mail via [Notifications](../features/notifications.md) or external SMTP settings.

## Related

- [Governance](governance.md)
- [Pack gate](governance.md#pack-gate-settingspack-gate)
