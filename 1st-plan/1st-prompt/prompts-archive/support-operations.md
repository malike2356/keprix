# keprix - Prompt: Support Infrastructure and Customer Success Operations

## Purpose

Prompt 39 established the support foundation: ticket intake, diagnostics bundles, incident logging, and customer success checklists. This prompt deepens the support infrastructure for production use, whether supporting self-host community users or managed commercial customers.

The goal: a support operator can triage, investigate, resolve, and communicate about any issue without leaving the keprix dashboard. Every resolution feeds back into the knowledge base so the next operator solves the same problem faster.

## Scope

Implement:

- Full ticket lifecycle management (triage, assignment, investigation, resolution, closure).
- Integrated knowledge base with article generation from resolved tickets.
- Customer-facing support portal (for managed customers).
- SLA tracking and breach alerts.
- Automated response suggestions using the keprix agent.
- Support analytics and reporting.
- Escalation rules and on-call rotation.
- Customer health scoring.
- Feedback collection and satisfaction tracking.
- Service status page generation.

## Output Paths

```
keprix/backend/support/
  __init__.py
  tickets.py              - ticket CRUD, lifecycle state machine, assignment
  knowledge.py            - knowledge base articles, search, generation from tickets
  portal.py               - customer-facing portal endpoints
  sla.py                  - SLA definition, tracking, alerting
  auto_response.py        - agent-powered response suggestions
  analytics.py            - support metrics, dashboards, reports
  escalation.py           - escalation rules, on-call schedules
  health_scoring.py       - customer health scoring model
  feedback.py             - CSAT and NPS collection
  status_page.py          - public status page generation
  schemas.py

keprix/backend/support/integrations/
  jira.py                 - Jira sync (optional)
  zendesk.py              - Zendesk migration/import
  linear.py               - Linear sync (optional)

keprix/ui/web/src/app/(workspace)/support/
  tickets/
    [id]/                 - ticket detail with timeline, diagnostics, resolution
    new/                  - ticket creation form
    queue/                - assigned queue, triage view
  knowledge/
    [id]/                 - article view and edit
    search/               - knowledge base search
  analytics/              - dashboard with metrics
  escalation/             - rules and on-call management
  health/                 - customer health dashboard
  feedback/               - survey results and trends

keprix/ui/web/src/app/(portal)/support/
  tickets/                - customer ticket view, creation
  knowledge/              - customer-facing knowledge base
  status/                 - public status page

keprix/docs/support/
  operator-guide.md
  sla-framework.md
  knowledge-base-guide.md

tests/support/
  test_tickets_lifecycle.py
  test_knowledge.py
  test_portal.py
  test_sla.py
  test_auto_response.py
  test_analytics.py
  test_escalation.py
  test_health_scoring.py
  test_feedback.py
  test_status_page.py
```

## Ticket Lifecycle Management

### State machine

```
NEW -> TRIAGE -> ASSIGNED -> INVESTIGATING -> WAITING_ON_CUSTOMER -> RESOLVED -> CLOSED
  |        |            |              |                    |              |
  |        |            |              +--> INVESTIGATING <--+              |
  |        |            |                                                    |
  +--> CLOSED (spam/duplicate)                                              |
  +--> CLOSED (withdrawn)                                                    |
```

Each state transition:

- Is timestamped and attributed to the operator or system action.
- Can trigger notifications (to customer, to assignee, to team).
- Has a required or optional comment.
- Is audit-logged.

### Triage queue

Unassigned tickets appear in the triage view, ordered by:

1. Priority (calculated from severity and customer tier).
2. Wait time (oldest first).
3. SLA breach risk (closest to breach first).

Triage actions:

- Assign to operator (self or other).
- Set priority.
- Set category and subcategory.
- Link to existing ticket (duplicate).
- Mark as spam.
- Request more information from customer.

### Ticket detail view

Each ticket shows:

- Full timeline (creation, triage, assignment, investigation notes, customer replies, resolution).
- Customer context (instance health, recent changes, previous tickets).
- Related knowledge base articles (auto-suggested).
- Diagnostics bundle (if attached).
- SLA clock with time remaining.
- Quick actions: reply, add internal note, escalate, resolve, close.

### Macros

Predefined responses for common scenarios:

```
/acknowledge  -> "Thanks for reporting this. I am looking into it now."
/need-info    -> "Could you share your keprix version and any relevant error messages?"
/resolved     -> "This should now be resolved. Please let me know if the issue persists."
/closed       -> "Closing this ticket as resolved. Feel free to reopen if needed."
/bug-filed    -> "I have filed this as a bug. Tracking reference: BUG-{id}."
```

Macros are customisable per team and can include template variables (`{customer_name}`, `{ticket_id}`, `{instance_version}`).

## Integrated Knowledge Base

### Article structure

```yaml
article:
  id: KB-00142
  title: "Database connection pool exhausted after upgrade to 2.1.0"
  status: published
  categories: [database, upgrade, performance]
  severity: medium
  applies_to_versions: ["2.1.0"]
  fixed_in_version: "2.1.1"
  created_from_ticket: TKT-00891
  content: |
    ## Symptoms
    - Backend returns 503 errors under load.
    - Logs show "Database connection pool exhausted".
    - Active connections at max (default 20).

    ## Cause
    keprix 2.1.0 reduced the default connection pool size from 50 to 20
    to accommodate lower-memory instances. High-traffic instances may
    exhaust this pool under load.

    ## Resolution
    1. Increase the pool size in .env:
       DATABASE_POOL_SIZE=50
    2. Restart the backend:
       docker compose restart backend
    3. Verify with health check.

    ## Prevention
    Monitor database connection count via the fleet dashboard.
    Set an alert at 80% of pool capacity.
```

### Article generation from tickets

When a ticket is resolved, the operator can click "Generate KB Article":

1. The agent analyses the ticket timeline, diagnostics, and resolution.
2. It drafts an article using the structure above.
3. The operator reviews, edits, and publishes.
4. The article is linked back to the source ticket.

### Search

The knowledge base supports:

- Full-text search across titles, content, and categories.
- Filter by category, severity, affected version.
- Related articles based on the current ticket context.
- "Was this helpful?" feedback on every article.

## Customer-Facing Support Portal

For managed customers, keprix provides a support portal:

### Portal features

- View all open and closed tickets.
- Create new tickets with category selection and file attachments.
- Reply to existing tickets.
- Search the knowledge base.
- View service status page.
- Access billing and account management.

### Portal authentication

- Customers authenticate with their keprix workspace credentials.
- Portal access is scoped to the customer's own data only.
- Option for SSO via OAuth2 (Google, GitHub, custom provider).

### Email-to-ticket

Customers can email `support@keprix.ai` to create tickets:

1. Inbound email is received via the email integration (Prompt 11).
2. A new ticket is created with the email subject as the title and body as the description.
3. Attachments are preserved and linked to the ticket.
4. Auto-reply confirms receipt with ticket ID.
5. Subsequent replies on the same thread update the ticket.

## SLA Tracking

### SLA definitions

Operators define SLAs per customer tier:

```yaml
sla_tiers:
  community:
    first_response: 48h
    resolution: null        # no commitment
    coverage: business_hours

  standard:
    first_response: 8h
    resolution: 72h
    coverage: business_hours

  premium:
    first_response: 1h
    resolution: 8h
    coverage: 24x7

  enterprise:
    first_response: 15m
    resolution: 4h
    coverage: 24x7
    dedicated: true          # dedicated support contact
```

### SLA clock

- First response clock starts when the ticket is created (or when business hours begin for business-hours SLAs).
- Resolution clock starts after first response.
- Clocks pause when waiting on customer.
- Clocks reset on reopen.

### SLA breach alerts

- Warning at 50% of SLA time remaining.
- Alert at 75%.
- Critical alert at 90%.
- Breach notification at 100% (to operator, team lead, and account manager if assigned).

### SLA reporting

Monthly SLA reports show:

- Total tickets, met SLA, breached SLA, percentage.
- Average first response time.
- Average resolution time.
- Breakdown by category and priority.
- Trend compared to previous month.

## Automated Response Suggestions

### Agent-powered suggestions

When an operator opens a ticket, the keprix agent analyses it and suggests:

1. **Related articles** from the knowledge base that may resolve the issue immediately.
2. **Similar tickets** that were resolved with solutions that may apply.
3. **Diagnostic questions** to ask the customer based on the symptoms described.
4. **Draft response** that the operator can review, edit, and send.

The agent does not auto-respond to customers. All responses require operator approval.

### Implementation

```python
class SupportAgent:
    """Analyses tickets and suggests responses, articles, and diagnostics."""

    def suggest(self, ticket: Ticket) -> SuggestionSet:
        """Return related articles, similar tickets, diagnostic questions,
        and a draft response for operator review."""

    def draft_response(self, ticket: Ticket, template: str) -> str:
        """Generate a draft customer response using a macro template."""

    def categorise(self, ticket: Ticket) -> Category:
        """Suggest category and priority based on ticket content."""
```

The suggestions are cached for 5 minutes to avoid repeated LLM calls during operator review.

## Support Analytics and Reporting

### Real-time dashboard

The support analytics dashboard shows:

- Open tickets (total, by status, by priority).
- Ticket volume (created vs resolved, by day/week/month).
- Average response and resolution time (by operator, by category).
- SLA compliance (overall, by tier, by operator).
- Customer satisfaction scores (CSAT, NPS trends).
- Knowledge base usage (top articles, search terms, helpfulness ratings).
- Operator workload (tickets per operator, resolution rate, average handle time).

### Scheduled reports

- Daily digest: new tickets, breached SLAs, unassigned tickets.
- Weekly summary: volume trends, top issues, team performance.
- Monthly review: full SLA report, customer health changes, knowledge base growth.

Reports are delivered via email, Slack, or available in the dashboard.

## Escalation and On-Call

### Escalation rules

```yaml
escalation_rules:
  - name: sla_breach_escalation
    condition: sla_breached
    escalate_to: team_lead
    after: 0m              # immediately on breach

  - name: severity_critical
    condition: severity == "critical"
    escalate_to: senior_engineer
    after: 30m             # if not responded in 30m

  - name: weekend_critical
    condition: severity == "critical" AND is_weekend
    escalate_to: on_call
    after: 5m
```

### On-call schedules

Operators define on-call rotations:

- Weekly rotation with primary and secondary.
- Schedule view with calendar integration (iCal export).
- Override for holidays and planned absence.
- Escalation path: primary -> secondary -> team lead -> engineering manager.

### On-call notifications

When escalated:

- Push notification via the keprix dashboard.
- Email to the on-call contact.
- Optional SMS for critical severity.
- Acknowledgement required within 5 minutes. If not acknowledged, escalate to the next level.

## Customer Health Scoring

### Health score model

Each customer gets a health score (0-100) based on:

| Signal | Weight | Green (>80) | Yellow (50-80) | Red (<50) |
| --- | --- | --- | --- | --- |
| Instance uptime (30d) | 25% | >99.9% | 99-99.9% | <99% |
| Open support tickets | 20% | 0 | 1-3 | >3 |
| SLA breaches (30d) | 15% | 0 | 1-2 | >2 |
| Version age | 15% | Current | 1 behind | >2 behind |
| Backup health | 15% | All passing | 1 failure | >1 failure |
| CSAT score (90d) | 10% | >4.0 | 3.0-4.0 | <3.0 |

### Health dashboard

- All customers ordered by health score (red at top).
- Click for detailed breakdown of each signal.
- Trend line showing score change over time.
- Automated alerts when score drops below a threshold.
- "At-risk" flag for customers trending downward for two consecutive weeks.

## Feedback and Satisfaction

### CSAT (Customer Satisfaction)

After ticket resolution, send a brief survey:

"Was this support interaction helpful?"

- Very satisfied
- Satisfied
- Neutral
- Dissatisfied
- Very dissatisfied

Optional free-text comment.

### NPS (Net Promoter Score)

Quarterly NPS survey to all managed customers:

"On a scale of 0-10, how likely are you to recommend keprix to a colleague?"

- Promoters (9-10)
- Passives (7-8)
- Detractors (0-6)

NPS = % Promoters - % Detractors.

### Feedback loop

- Detractor responses trigger an automatic follow-up ticket for a support manager.
- All free-text comments are reviewed weekly.
- Top themes from feedback are summarised and shared with the product team.

## Service Status Page

### Public status page

A publicly accessible page at `status.keprix.ai` showing:

- Current status of all services (operational, degraded, outage, maintenance).
- Incident history (last 90 days).
- Upcoming maintenance windows.
- Subscribe to updates (email, RSS, webhook).

### Status updates

During an incident, operators post updates:

1. **Investigating**: "We are investigating reports of elevated error rates on the API."
2. **Identified**: "The issue has been traced to a database connection pool exhaustion. We are scaling up the pool."
3. **Monitoring**: "The fix has been deployed. Error rates have returned to normal. We are monitoring."
4. **Resolved**: "The incident is resolved. A post-mortem will be published within 5 business days."

Updates are timestamped and visible on the status page and sent to subscribers.

### Automated status

The status page integrates with fleet health monitoring (Managed Ops prompt):

- If an instance fails health checks, the status page automatically updates to "degraded".
- If multiple instances fail, status changes to "outage".
- Recovery triggers automatic "operational" status.

## Tests

```
tests/support/
  test_tickets_lifecycle.py     - state transitions, required fields, notifications
  test_ticket_assignment.py     - auto-assign, round-robin, load balancing
  test_knowledge_search.py      - full-text search, filters, related articles
  test_knowledge_generation.py  - article draft from resolved ticket
  test_portal.py                - customer access control, ticket creation, replies
  test_sla.py                   - clock pausing, breach alerts, reporting
  test_auto_response.py         - suggestion quality, caching, approval flow
  test_analytics.py             - dashboard metrics, scheduled reports
  test_escalation.py            - rule evaluation, on-call notification, acknowledgement
  test_health_scoring.py        - score calculation, alerts, trend detection
  test_feedback.py              - CSAT collection, NPS calculation, detractor follow-up
  test_status_page.py           - incident lifecycle, subscription, automated updates
  test_email_to_ticket.py       - inbound email parsing, attachment handling
```

## Acceptance Criteria

- A ticket moves through the full lifecycle (NEW -> TRIAGE -> ASSIGNED -> INVESTIGATING -> RESOLVED -> CLOSED) with all required fields validated.
- Resolving a ticket and clicking "Generate KB Article" produces a draft article with symptoms, cause, resolution, and prevention sections.
- A customer can create, view, and reply to tickets through the support portal without seeing other customers' data.
- An SLA breach at the warning threshold generates an alert to the assigned operator.
- An SLA breach at 100% escalates to the team lead and is reflected in the monthly SLA report.
- The support agent suggests at least one relevant knowledge base article for 80% of tickets based on title and description.
- Customer health scores update daily and trigger alerts when a customer moves from green to yellow or red.
- The status page updates to "degraded" within 2 minutes of a health check failure detected by fleet monitoring.
- CSAT surveys are sent within 24 hours of ticket resolution and results appear in the analytics dashboard.
