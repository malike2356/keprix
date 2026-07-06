# Extraction rules

Formal workflow for learning from Carina and Aiva without copying private implementation.

## Do not copy

- Production `.env` files
- Customer data or private tenant records
- Private Scout server code
- Aiva Keys and `keys.carinaai.uk`
- Paid enterprise-only controls as free features
- Stripe live credentials
- Operational secrets and internal-only runbooks
- Proprietary customer workflows not intended for the public product

## Classification table

| Class | Meaning | Keprix action |
| --- | --- | --- |
| `public_core` | Suitable for free self-host | Rebuild in Keprix |
| `public_optional` | Useful but dependency-heavy | Optional plugin or Hub pack |
| `paid_managed` | Aiva managed SaaS | Stub or integration hook only |
| `scout_enterprise` | Paid governance control | Gate behind Scout connection |
| `unsafe_or_private` | Not suitable | Do not port |

## Workflow

1. **Scan** Carina core and Aiva app directories read-only (`keprix.extraction.scanner`).
2. **Inventory** features by subsystem with owner, source path, and target prompt (`inventory.yaml`).
3. **Mark** dependencies, data touched, secrets touched, and tenant scope per feature.
4. **Classify** each feature (`keprix.extraction.classifier`).
5. **License check** referenced files for proprietary or copyleft conflicts (`license_check.py`).
6. **Secret check** block patterns and credential file extensions (`secret_check.py`).
7. **Conflict check** against Keprix free self-host position (no remote keys, no Aiva upsell).
8. **Rebuild plan** for every port candidate; never blind copy.
9. **Test map** Carina behavioral tests to Keprix test paths.
10. **Report** boundary summary (`build_boundary_report()`).

## Tooling

```bash
cd /opt/lampp/htdocs/verlox/keprix
.venv/bin/python -c "
from keprix.extraction.report import build_boundary_report
report = build_boundary_report()
print(report['by_classification'])
print('validation:', report['validation_errors'])
"
```

## Output artifacts

| Path | Purpose |
| --- | --- |
| `product/boundaries/carina-feature-inventory.md` | Subsystem inventory index |
| `product/boundaries/carina-to-keprix-map.md` | Carina source to Keprix target |
| `product/boundaries/aiva-to-keprix-map.md` | Aiva commercial boundary |
| `product/boundaries/enterprise-gates.md` | Scout enterprise gating |
| `product/boundaries/rejected-features.md` | Features with rejection reasons |
| `src/keprix/extraction/inventory.yaml` | Machine-readable inventory |
