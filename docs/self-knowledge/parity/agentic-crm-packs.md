# Agentic CRM packs (self-knowledge)

Vertical packs under src/keprix/discovery/packs/:

- generic: enabled companies_house, csv_import, web_directory, fake. Docs
  docs/features/crm-packs/generic.md
- property: property_csv, companies_house, web_directory enabled; rightmove_http
  and zoopla_http flagged stubs (KEPRIX_PROPERTY_PORTAL_ADAPTERS). Docs
  docs/features/crm-packs/property.md
- health_social: health_csv, directory_web, companies_house enabled; cqc_api stub;
  soft_wall_enroll_always; no patient data. Docs
  docs/features/crm-packs/health_social.md

Social API discovery (LinkedIn/Meta/TikTok) is API-first stub; scrape off.

Pack manifests declare adapters, sheet types, contactability defaults, and
outreach_allowed. Degraded adapters return not_configured honestly.
