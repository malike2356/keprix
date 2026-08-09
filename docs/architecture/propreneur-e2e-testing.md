# Propreneur real e2e testing (prompt 642)

## Database

Designated Pest/CI DB: `propreneur_testing_agent` (writable `public` + pgvector).

```bash
cd /opt/lampp/htdocs/verlox/propreneur
bash scripts/bootstrap-testing-postgres.sh
bash scripts/preflight-testing-db.sh
```

Details: `propreneur/docs/aiva/TESTING-POSTGRES.md`.

## Two-process harness

```bash
bash /opt/lampp/htdocs/verlox/keprix/scripts/propreneur-e2e-harness.sh
```

Runs:

1. Propreneur Pest: API, CRUD matrix, security fail-closed (real controllers, tenancy, PostgreSQL).
2. Mints two-tenant fixtures and starts `php artisan serve`.
3. Keprix pytest: pack regressions + `tests/e2e_propreneur/` against the live connector (Host + Bearer grant; Soft Wall; SSRF/circuit/node kill).
4. Writes `docs/architecture/propreneur-e2e-evidence.v1.json` mapping every `live` / `approval_required` capability to tests.

Provider/LLM may be faked. Propreneur controllers/DB and Keprix connector/handlers/agent adapter must stay real.
