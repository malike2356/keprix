---
name: channel-shield
description: Triage Channel Shield quarantine, explain reports, and channel-aware tips.
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  keprix:
    tags: [security, channel-shield, quarantine, email, slack, scout]
    related_skills: [configure-channel, configure-scout]
    risk: high
---

# Channel Shield

Use when the operator asks about inbound phishing, quarantine, Channel Shield protections, or safe summaries across email and messaging channels.

## Tools / actions

1. List quarantine: prefer UI `/channel-shield` or API `GET /api/channel-shield/messages?status=quarantined`.
2. Explain report: `GET /api/channel-shield/messages/{id}/report` (stages, hashes, verdict, Scout ids).
3. Release: `POST /api/channel-shield/messages/{id}/release` (malicious requires admin / dual control).
4. Destroy: `POST /api/channel-shield/messages/{id}/destroy` (admin only; high risk; confirm twice).
5. Doctor: `keprix channel-shield doctor`.

## Channel tips

- **email**: MX/subdomain or shadow mailbox; SPF/DKIM/DMARC in authSignals.
- **slack**: Not transparent intercept; verify signing secret; never re-share malicious files.
- **teams**: Bot Framework / Graph admin consent.
- **telegram / whatsapp / discord**: Download media to immutable store before analysis; never forward live malware.
- **sms**: Truncate safe summary; include UI deep link.
- **web**: Check CORS origins and embed key.

## Safety

Never paste live malicious payloads, credentials, or raw attachment bytes into chat. Summaries only.
Release and destroy are high-risk tools and require explicit operator approval.

## Agent OS

Before building prompts or calling tools on a shielded item:

1. Call `POST /api/channel-shield/agent/guard` or open the employee action drawer.
2. Use only `agentSafeContent` (never rawEvidenceRef contents).
3. Memory: incident records only for suspect/malicious (`[channel-shield-incident]` + `channel_shield_message_id=`).
4. Outbound replies must not quote payloads or open quarantined links.

## Tool risk

| Action | Risk | Approval |
| --- | --- | --- |
| list / explain | low | no |
| request release | medium | yes |
| release | high | admin / security |
| destroy | high | admin only |
