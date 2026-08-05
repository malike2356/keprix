# Ponytail ladder

The Ponytail ladder is enabled by default for Keprix coding sessions in `full` mode. It asks the coding agent to stop at the first rung that holds: YAGNI, reuse existing code, use stdlib, use native platform features, use installed dependencies, make it one line, and only then write the minimum code that works.

Endpoints:

- `GET /api/coding/ladder/mode`
- `PUT /api/coding/ladder/mode`
- `POST /api/coding/ladder/review`
- `GET /api/coding/ladder/audit`
- `GET|POST /api/coding/ladder/debt`
- `POST /api/coding/ladder/debt/harvest`
- `GET /api/coding/ladder/metrics`

Dashboard: `/coding/ladder`.
