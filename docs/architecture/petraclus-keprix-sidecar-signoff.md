# Petraclus Keprix sidecar sign-off

**Verdict: READY** (staging pilot with fixture assets only)

**Date:** 2026-08-08
**Pack:** `domain-packs/petraclus` version `0.1.0`
**Contract:** `1.0.0`
**Port:** 3362

## Threat model summary

Petraclus remains source of truth for targets, grants, findings, licences and UI.
Keprix explains and proposes under six-layer isolation. Active and mutate actions
require exact target grant, approval and edition entitlements, revalidated each time.
Exploit automation and remediation execute are off. Scanner/feed text is untrusted.

## Pack checksum note

Compute after install:

```bash
cd /opt/lampp/htdocs/verlox/keprix
find domain-packs/petraclus -type f ! -path '*/provisioning/receipt-*' -print0 \
  | sort -z | xargs -0 sha256sum | sha256sum
```

Record the aggregate digest in the pilot receipt. Provision receipts set
`secrets_included: false` and never mint licences.

## Rollback

```bash
curl -X POST http://127.0.0.1:3362/v1/products/petraclus/rollback \
  -H 'Content-Type: application/json' \
  -d '{"to_pack_version":"0.0.1"}'
```

Risky action nodes stay disabled until explicit operator approval on upgrade.

## Air-gap evidence pointers

- `domain-packs/petraclus/airgap/bundle.manifest.json` (`phone_home: false`)
- `GET /v1/products/petraclus/airgap/bundle`
- `docs/pilot-runbook.md`, `docs/threat-model.md`, `docs/ARCHITECTURE.md`

## Test evidence

```bash
.venv/bin/python -m pytest domain-packs/petraclus/tests -q
```

Pilot scope: fixture workspaces `ws-alpha` / `ws-beta` / `ws-team` only. No public/live targets.
