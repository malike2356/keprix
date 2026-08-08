# WhatsApp Business and SMS (Nice 459)

Official-provider path only. Default **off**.

## Prerequisites

1. Consent / suppression Must (448) exists
2. Owner sets `KEPRIX_WHATSAPP_SMS=1`
3. Soft Wall enable workspace toggle
4. Channel-specific consent (`sms` / `whatsapp`), not email alone
5. Approved channel template Soft Wall
6. First send Soft Wall always on

## Credentials

- WhatsApp: `KEPRIX_WHATSAPP_TOKEN` (or Meta WhatsApp token aliases)
- SMS: `KEPRIX_TWILIO_AUTH_TOKEN` + `KEPRIX_TWILIO_ACCOUNT_SID`

Missing keys return `not_configured`.

## Explicit non-goal

Unofficial WhatsApp Web / personal account automation.
