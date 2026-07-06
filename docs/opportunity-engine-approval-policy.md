# Opportunity Engine approval policy

Risky execution actions are blocked until an operator explicitly approves or rejects them. The launch orchestrator and growth loop reference these gates; live integrations stay idle until approval is recorded in `13-approval-log.md`.

## Risky actions

| Action key | Operator label |
| --- | --- |
| `send_outreach` | Sending outreach |
| `publish_post` | Publishing posts |
| `create_ad` | Creating ads |
| `edit_ad` | Editing ads |
| `spend_money` | Spending money |
| `update_crm` | Updating CRM records |
| `send_email_sequence` | Sending email sequences |
| `publish_landing_page` | Publishing landing pages |
| `charge_customer` | Charging customers |
| `export_personal_data` | Exporting personal data |
| `upload_lead_list` | Uploading lead lists |
| `set_ad_budget` | Setting ad budgets |
| `create_stripe_product` | Creating Stripe products or prices |

Implementation: `src/keprix/opportunity/approvals.py`.

## Default behaviour

- **Launch orchestrator** runs in **dry run** unless `launch_dry_run` is set to `false` in opportunity metadata and approvals are granted.
- **Validation score** below 65 blocks the asset factory playbook unless `validation_override` is set with operator intent.
- **Regulated industries** (healthcare, finance, legal, and similar) receive warnings in offer and launch artifacts; operators must review compliance before approval.
- **No private data collection by default**: lead lists, personal exports, and CRM bulk updates require explicit approval.

## Approving from CLI

```bash
keprix opportunity approve opp-xxxxxxxx create_ad --approve
keprix opportunity approve opp-xxxxxxxx spend_money --reject --reason "Budget not allocated"
```

## Approving from API

Use `POST /api/opportunities/{id}/approve` with `action`, `decision` (`approve` or `reject`), and optional `reason`.

## Approval log artifact

`13-approval-log.md` is a markdown table with timestamp, action, risk level, decision, and detail. Dry-run launch plans list pending gates without executing them.

## Web UI

The opportunities detail view surfaces pending approvals and links to the launch plan. Operators should resolve gates before disabling dry run or connecting live ad spend.

## What does not require approval

Research playbooks, markdown artifact generation, validation scoring, dry-run launch planning, and manual import templates for missing integrations are safe by default and do not spend money or publish externally.
