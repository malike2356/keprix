# Customer Concierge v1 release evidence (Prompt 635)

**Programme:** keprix-customer-concierge-booking (628-635)  
**Contract version:** 1.0.0  
**Runtime dependency:** none (standalone Keprix)

## Identity

| Field | Value |
| --- | --- |
| Product | Keprix Customer Concierge |
| Contract | `contracts/customer-concierge-v1/` (1.0.0) |
| Series prompts | 628-635 |
| Release date | 2026-08-09 |
| Git root | `keprix/` |

## Git pin

| Root | Branch | SHA | Notes |
| --- | --- | --- | --- |
| keprix/ | main | fill-at-ship | Contabo rsync mirror must match push |

## Proof commands (local)

```bash
cd /opt/lampp/htdocs/verlox/keprix
python -m pytest tests/customer_concierge/ -q
bash scripts/smoke-customer-concierge-docker.sh
bash /opt/lampp/htdocs/verlox/scripts/guard-public-github-hygiene.sh
```

## Contabo deploy

```bash
rsync -az --delete \
  --exclude '.git/' --exclude '.env' --exclude '.env.*' --exclude '!.env.example' \
  --exclude '.keprix/' --exclude '.keprix-data/' --exclude 'keprix-data/' \
  --exclude '1st-plan/' --exclude 'apps-on-keprix/' \
  --exclude 'node_modules/' --exclude 'frontend/node_modules/' --exclude 'frontend/.next/' \
  --exclude '.venv/' --exclude 'venv/' --exclude '__pycache__/' \
  /opt/lampp/htdocs/verlox/keprix/ \
  malike@80.190.81.208:/home/malike/apps/keprix/

ssh malike@80.190.81.208 'cd /home/malike/apps/keprix && docker compose \
  --project-directory /home/malike/apps/keprix \
  --env-file /home/malike/apps/keprix/.env \
  -f deploy/contabo/docker-compose.app.yml up -d --build'
```

## Public health (mandatory)

| URL | Expect |
| --- | --- |
| https://app.keprixai.com/ | 200 |
| https://app.keprixai.com/api/health | 200 |
| https://keprixai.com/ | 200 |
| https://carinaai.uk/ | 200 |

## Honesty

- No required Carina service
- Static room URL and ICS are labelled unmanaged fallbacks
- Capability health never fakes Zoom/Google ready without credentials
- Fixture MANIFEST signature is content integrity, not a secret credential

## Rollback

Redeploy previous Contabo rsync tree + compose rebuild. Unpublish concierge if visitor impact remains. Do not wipe customer SQLite/Postgres.

## Evidence artifact

`docs/architecture/evidence/customer-concierge-conformance-635.json`
