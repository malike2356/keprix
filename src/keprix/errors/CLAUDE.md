# Public / private error handling (Keprix)

Never return raw exceptions, stacks, SQL, or paths in API responses.
Use `keprix.errors.create_public_error` / `public_http_payload`.
Wrap jobs and payment callbacks with `job_error_boundary` / `payment_error_boundary`.
Search private logs via `/api/errors/search` and `/api/errors/{reference}`.
