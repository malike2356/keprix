# DSAR requests

Operator endpoints (admin):
- POST /api/governance/dsar/export (fulfills via privacy DsarStore -> JSON export)
- POST /api/governance/dsar/delete (confirm=true runs erase_user_data)
- GET /api/governance/dsar/requests

Also available: /api/privacy/dsar and /api/privacy/erase.
Exports include memories, consents, research jobs, contacts, leads, tenant memberships.
