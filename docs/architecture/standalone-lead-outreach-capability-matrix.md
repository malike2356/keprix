# Standalone lead and outreach capability matrix (Prompt 620)

**Status:** BASELINE LOCKED  
**Date:** 2026-08-09  
**Series:** `keprix-standalone-lead-outreach` (620-628)  
**Depends on:** Archived Visual Agentic CRM (`keprix-agentic-crm-lead-gen`, docs/architecture/agentic-crm-*)

Classification: **REAL** | **PARTIAL** | **SIMULATED** | **MANUAL** | **MISSING** | **BLOCKED_OPTIONAL_CREDENTIALS**

Honesty rule: UI presence or mocked tests alone never mark REAL. Conformance suite: `tests/crm/test_standalone_outreach_conformance.py`. Do not mark complete from UI alone.

## Reuse (authoritative existing surfaces)

| Surface | Keep |
| --- | --- |
| Packages | `src/keprix/crm/`, `src/keprix/outreach/`, `src/keprix/discovery/`, `src/keprix/sheet_preprocess/`, Soft Wall, Companies House, viCal, email accounts |
| HTTP | `/api/crm/*`, `/api/outreach/*`, `/api/crm/sheets/*`, `/api/crm/discovery/*` |
| Stages SoT | `CrmStage` in `crm/models.py` (map outreach pipeline statuses; do not invent a third vocabulary) |
| Soft Wall gates | Existing `CRM_GATES` / outreach approvals; extend payloads, do not fork a second approval system |
| GUI | `/crm/*` and `/outreach/*` |

## Capability matrix

| Capability | Class | Evidence / gap |
| --- | --- | --- |
| Lead discovery (adapter jobs → CRM list) | REAL | `discovery/runner.py`, `/api/crm/discovery/run`, `/crm/discover` |
| Social / portal HTML scraping | SIMULATED | Social scrape refused; property portals stubbed by policy |
| Web directory discovery | PARTIAL | Adapter exists; needs search backend; Soft Wall on fetch |
| Companies House discovery + import | BLOCKED_OPTIONAL_CREDENTIALS | REAL when `COMPANIES_HOUSE_API_KEY`; else not_configured |
| Listing-page HTML ingestion | SIMULATED | Portals stub; intentional Soft Wall / legal checklist |
| CSV import | REAL | Discovery CSV, sheet upload, outreach lead import |
| TSV import | REAL | Sheet preprocess suffixes |
| XLSX import | REAL | openpyxl path |
| XLS (legacy) | REAL | `crm/ingestion/readers.py` via xlrd (`keprix[analytics]`) |
| ODS | REAL | `crm/ingestion/readers.py` via odfpy (`keprix[analytics]`) |
| Google Sheet | BLOCKED_OPTIONAL_CREDENTIALS | Routes exist; needs Google credentials |
| Pasted-row import | REAL | `ingest_row_array` / tools `crm_ingest_import` rows payload |
| API import | REAL | CRM upsert + discovery + ingest tools |
| Channel-attachment import | PARTIAL | Parser path REAL via `ingest_channel_attachment`; mailbox poller still stub (`email_ingest.py`) |
| Exact dedup | REAL | email → phone → website+company+locality (`crm/ingestion/dedup.py`) |
| Fuzzy merge | REAL | Soft Wall `merge_identity` |
| Sheet Soft Wall enrichment | REAL | `/crm/enrich` propose/apply |
| Licensed enrichment providers | BLOCKED_OPTIONAL_CREDENTIALS | Connection slots; Soft Wall without live keys |
| Provenance | REAL | `crm_field_provenance` |
| Contacts / Accounts | REAL | CRUD APIs + GUI |
| Customer / paying conversion | REAL | Soft Wall `stage_customer_paying` |
| Spreadsheet CRM editable grid | REAL | `/crm/leads` DataGrid + keyset/bulk/views/export/ingest APIs (`CrmLeadsDataGrid`, `tests/crm/test_leads_grid_api.py`) |
| Lists | REAL | CRM + outreach lists |
| Campaigns / sequences | REAL | Outreach store + GUI |
| Scheduling / process-due | REAL | `process_due` + cron seeds |
| Soft Wall approvals | REAL | CRM gates + outreach send approvals |
| Live email send | PARTIAL | Default `KEPRIX_OUTREACH_DRY_RUN=1`; account bind incomplete (Prompt 625) |
| Provider events (bounce/complaint) | MISSING | No SES/SendGrid/Mailgun normalizer (Prompt 625) |
| Reply ingest API | REAL | Manual/API inbound classify |
| Automatic mailbox reply scan | PARTIAL | Stub / agent prompt seed (Prompt 626) |
| Bookings (viCal) | REAL | CRM offer-booking + outreach bookings |
| Nurture | REAL | `crm/nurture.py` + workflows |
| Suppression | REAL | Suppression wins over enroll/send |
| Attribution | REAL | `/crm/attribution` |
| Agent tool initiation | REAL | crm / outreach / sheet / discovery tools |
| Channel (Telegram) initiation | PARTIAL | Funnel intents; not full sheet→campaign journey (Prompt 627) |
| CLI initiation | REAL | `keprix crm-ingest` + `python -m keprix.crm.ingestion` |
| API / frontend initiation | REAL | Documented APIs + full consoles |
| Local single-user persistence | REAL | `crm.sqlite` + `outreach.sqlite` |
| Hosted multi-workspace persistence | REAL | SQLite CE + Postgres TEXT schema (`durable.py`, Alembic 028); workspace scoped queries |

## Build order (series)

| Prompt | Focus | Depends on |
| --- | --- | --- |
| 620 | This matrix + contract + conformance gaps | Owner approval |
| 621 | Canonical lead schema + spreadsheet ingestion (XLS/ODS/paste honesty) | 620 |
| 622 | Durable storage + tenant isolation (CRM Postgres path) | 621 |
| 623 | Production spreadsheet CRM UI | 622 (parallel with 624 OK) |
| 624 | Durable campaign/sequence scheduler | 622 |
| 625 | Approved email delivery + provider events | 624 |
| 626 | Automatic mailbox replies | 625 |
| 627 | Funnel nurture + channel orchestration | 625+ |
| 628 | E2E observability, release, deploy | all prior |

## Test commands

```bash
# Prompt 620 conformance (documents gaps; readiness must stay false until series closes)
cd /opt/lampp/htdocs/verlox/keprix
python -m pytest tests/crm/test_standalone_outreach_conformance.py -q

# Existing CRM/outreach regression (do not treat green UI tests as live-send readiness)
python -m pytest tests/crm tests/tools/test_outreach_automation.py tests/discovery -q --tb=line
```

## Dual-store hazard (must resolve in 621-622)

Outreach `PIPELINE_STAGES` (`new`, `enrolled`, `contacted`, …) differ from CRM `CrmStage`. Standalone contract SoT is **CRM stages**; outreach statuses map into them. Do not create a third vocabulary.
