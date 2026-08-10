# Session policy (Keprix)

Password change MUST revoke all sessions immediately.
Configure `KEPRIX_SESSION_TIER` (financial|business|content) and optional
`SESSION_IDLE_TIMEOUT_MS`, `SESSION_ABSOLUTE_MAX_MS`, `SESSION_MAX_CONCURRENT`.
Default concurrent limit is 5. New device logins raise a banner/email hook via
`keprix.sessions.NEW_DEVICE_NOTIFIER`.
