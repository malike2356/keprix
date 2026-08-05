# Scout Warden (CE)

Disabled by default. Enable with KEPRIX_SCOUT_WARDEN_ENABLED=1 and KEPRIX_SCOUT_WARDEN_URL.
Token from .access via KEPRIX_SCOUT_WARDEN_TOKEN (never commit).

POST /api/scout-warden/scans degrades when Scout is down.
POST /api/scout-warden/alerts persists to scout signal_log and Channel Shield bridge.
