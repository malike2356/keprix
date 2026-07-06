# jamovi export bridge

Keprix exports analytics datasets and analysis plans for jamovi. The bridge is API-driven; jamovi itself runs outside Keprix.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/analytics/jamovi/export` | Build an export package from a dataset |
| `POST` | `/api/analytics/jamovi/export/download` | Download the generated package |
| `GET` | `/api/analytics/jamovi/modules` | List supported jamovi modules |
| `POST` | `/api/analytics/jamovi/plan` | Generate an analysis plan |
| `POST` | `/api/analytics/jamovi/r-syntax` | Capture R syntax for reproducibility |

See the auto-generated [API reference](../reference/api.md) for request schemas.

## Workflow

1. Import or register a dataset in the research workspace.
2. Call `/api/analytics/jamovi/plan` with the analysis goal.
3. Export with `/api/analytics/jamovi/export` and open the package in jamovi.
4. Store external results back on the research project artifact timeline.

## Boundaries

Keprix does not ship the jamovi GUI. Operators install jamovi locally or on a separate host. Offensive or unrelated analytics stay out of scope for this bridge.
