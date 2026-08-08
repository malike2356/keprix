# Property portal adapters: legal checklist (not legal advice)

**Status:** experimental, default **OFF**  
**Flag:** `KEPRIX_PROPERTY_PORTAL_ADAPTERS=1`  
**Adapters:** `rightmove_http`, `zoopla_http`

## Operator checklist before enabling

1. Confirm you have a lawful basis and licence / API agreement for any portal data you ingest.
2. Prefer official APIs or licensed data feeds over HTML scraping.
3. Read the portal Terms of Use. Many portals prohibit scraping, bulk extraction, and automated access.
4. Acknowledge Soft Wall approval in Keprix before any experimental portal run (`legal_checklist_acknowledged=true`).
5. Do not advertise or UI-claim "we scrape Zoopla/Rightmove" unless the flag is on and this checklist is acknowledged.
6. Keep scrapers feature-flagged off in production by default.
7. Prefer always-on paths: `property_csv`, Companies House (`companies_house`), and `web_directory`.

## What Keprix does by default

- Property CSV and sheet preprocess work without portal adapters.
- Portal HTTP adapters refuse when `KEPRIX_PROPERTY_PORTAL_ADAPTERS` is unset/0.
- Even when the flag is on, Keprix refuses HTML scrape without credentials + checklist ack.

## Risk note

HTML scrape of property portals often violates Terms of Service and may create legal and account risk. This document is an operator checklist, not legal advice.
