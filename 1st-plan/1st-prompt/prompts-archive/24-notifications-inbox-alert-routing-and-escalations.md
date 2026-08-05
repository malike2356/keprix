# keprix - Prompt 24: Notifications, Inbox, Alert Routing, And Escalations

## Purpose

Build one notification and escalation system across web, mobile, email, Telegram, Slack, Discord, WebChat, TUI, CLI, Scout-connected workflows, jobs, billing, setup, and security.

Users should not need to hunt across surfaces to understand what needs attention.

## Scope

Implement:

- Unified inbox.
- Notification preferences.
- Channel routing.
- Escalation policy.
- Delivery receipts.
- Retry logic.
- Quiet hours.
- Digest emails.
- Mobile push.
- In-app notifications.
- Approval reminders.
- Job failure alerts.
- Billing alerts.
- Security alerts.
- Scout alerts where connected.

## Output Paths

```text
keprix/backend/notifications/
  __init__.py
  inbox.py
  router.py
  preferences.py
  channels.py
  escalation.py
  delivery.py
  digest.py
  templates.py
  schemas.py

keprix/ui/web/notifications/
keprix/ui/mobile/notifications/
keprix/tests/notifications/
```

## Notification Types

Support:

- Approval needed.
- Job complete.
- Job failed.
- Scheduled task failed.
- Setup needs attention.
- Credential expiring.
- Usage limit warning.
- Billing failed.
- Subscription changed.
- Security alert.
- Scout policy alert.
- Data import complete.
- Research complete.
- ML experiment complete.

## Routing Rules

Routing must consider:

- User role.
- Workspace policy.
- Notification severity.
- Channel availability.
- User preference.
- Quiet hours.
- Escalation delay.
- Whether the notification contains sensitive data.

Sensitive alerts must not be posted into public channels.

## Tests

Add tests for:

- Notification appears in unified inbox.
- Sensitive notification is not sent to group chat.
- Quiet hours delay non-critical notification.
- Critical alert bypasses quiet hours where policy allows.
- Approval reminder escalates after timeout.
- Delivery failure retries.
- User preference suppresses allowed channel.

## Acceptance Criteria

- keprix has one notification center.
- Alerts route consistently across surfaces.
- Sensitive data is protected.
- Escalations are auditable.
- Users can control notification preferences.
