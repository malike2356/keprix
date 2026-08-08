# Health and social care vertical pack

Pack id: `health_social`  
Sheet types: `clinic_referrals`, `care_providers`, `practitioners`

## Scope (hard)

Discovery and CRM lists for this pack cover **organisations and professional contacts only**.

Never import patient, service-user, NHS number, diagnosis, or clinical record fields into discovery candidates or CRM leads from this pack.

## Adapters

| Adapter | Notes |
| --- | --- |
| `health_csv` | Care-provider CSV; rejects obvious patient-data columns |
| `cqc_api` | Honest stub until API credentials / public mode configured |
| `directory_web` | Reuses web directory with care-oriented query templates |

## Soft Wall (always-on for enroll)

Health/social care outreach is high-risk. List enroll (`approve_list_enroll`) requires Soft Wall even if the workspace has loosened other CRM Soft Wall gates.

## Compliance note (not legal advice)

UK care and health marketing is tightly regulated. Operators should consider PECR/UK GDPR, NHS/CQC expectations, and professional advertising rules before any outreach. Keprix Soft Wall and contactability gates support review; they are not a substitute for legal advice.
