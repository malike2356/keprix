# CRM pack: health and social care

Pack id: `health_social`  
Manifest: `src/keprix/discovery/packs/health_social.yaml`  
Also: `docs/features/health-social-care-pack.md`

Organisations and professional contacts for care providers and clinics only.

## Hard scope

Never import patient, service-user, NHS number, diagnosis, or clinical record
fields into discovery candidates or CRM leads from this pack.

## Adapters

| Adapter | Status | Notes |
| --- | --- | --- |
| `health_csv` | Enabled | Rejects obvious patient-data columns |
| `directory_web` | Enabled | Care-oriented directory templates |
| `companies_house` | Enabled | Org research |
| `web_directory` | Enabled | Shared directory adapter |
| `cqc_api` | Stub | Honest `not_configured` until credentials / public mode |

## Soft Wall

`soft_wall_enroll_always: true`. List enroll requires Soft Wall even if other
CRM gates are loosened for the workspace.

## Sheet types

`clinic_referrals`, `care_providers`, `practitioners`.

## Compliance note

Not legal advice. UK care and health marketing is tightly regulated. Soft Wall
and contactability support review; they do not replace legal counsel.
