# Opportunity Engine integrations

Launch orchestration and the growth loop discover optional integrations before suggesting live tasks. Discovery is **best effort**: missing connectors produce setup instructions and manual import fallbacks, not hard failures.

Implementation: `src/keprix/opportunity/integrations.py`.

## Supported integration kinds

| Kind | Purpose |
| --- | --- |
| `crm` | Contacts and pipeline updates |
| `email` | Sequences and transactional send |
| `ads` | Paid campaign creation |
| `social` | Organic post publishing |
| `website` | Landing page deploy |
| `analytics` | Traffic and conversion readback |
| `stripe` | Products, prices, checkout |
| `calendar` | Booking and follow-up scheduling |
| `forms` | Lead capture tools |

## Connection methods

### 1. Keprix settings (preferred)

Connect services through the workspace UI where available (email accounts, contacts, billing for Stripe, and similar). The integration probe uses native stores when present.

### 2. Environment flags (automation and CI)

Set any of the following to `connected`, `true`, `1`, or `yes`:

```bash
export KEPRIX_INTEGRATION_CRM=connected
export KEPRIX_INTEGRATION_EMAIL=connected
export KEPRIX_INTEGRATION_ADS=connected
export KEPRIX_INTEGRATION_SOCIAL=connected
export KEPRIX_INTEGRATION_WEBSITE=connected
export KEPRIX_INTEGRATION_ANALYTICS=connected
export KEPRIX_INTEGRATION_STRIPE=connected
export KEPRIX_INTEGRATION_CALENDAR=connected
export KEPRIX_INTEGRATION_FORMS=connected
```

### 3. Per-opportunity overrides

In `opportunity.json`, set `integrations_config`:

```json
{
  "integrations_config": {
    "email": true,
    "crm": false,
    "ads": true
  }
}
```

Overrides take precedence over environment probes for that opportunity only.

## CRM

Connect contacts under **Settings > Contacts** or set `KEPRIX_INTEGRATION_CRM=connected`. CRM updates remain behind the `update_crm` approval gate.

## Email

Add an email account under **Settings > Email** or set `KEPRIX_INTEGRATION_EMAIL=connected`. Sequences require `send_email_sequence` approval.

## Ads

Connect an ads manager integration or set `KEPRIX_INTEGRATION_ADS=connected`. Creating or editing campaigns requires `create_ad`, `edit_ad`, or `set_ad_budget` approval.

## Social

Link a social publishing account or set `KEPRIX_INTEGRATION_SOCIAL=connected`. Publishing requires `publish_post` approval.

## Website / landing pages

Configure a deploy target or set `KEPRIX_INTEGRATION_WEBSITE=connected`. Publishing requires `publish_landing_page` approval.

## Analytics

Connect GA4, Plausible, or another analytics provider, or set `KEPRIX_INTEGRATION_ANALYTICS=connected`. The growth loop uses analytics for experiment ranking when connected; otherwise it documents manual metric import.

## Stripe

Add Stripe API keys in billing settings or set `KEPRIX_INTEGRATION_STRIPE=connected`. Product creation requires `create_stripe_product` approval; charging requires `charge_customer` approval.

## Scout connectors (optional)

Scout governance bridges (vault keys, webhook policies) can supply external research signals. They are **optional**: opportunity playbooks run without Scout. When Scout is unavailable, competitor and demand playbooks rely on built-in templates and operator-provided context.

## Growth loop without integrations

When analytics or ads are missing, `14-growth-loop.md` includes a manual metrics import table and ranked experiments that do not call external APIs.

## Dry run default

Even with all integrations connected, the launch orchestrator defaults to dry run. Live connector calls for risky actions only proceed after explicit approval and `launch_dry_run: false` in metadata.
