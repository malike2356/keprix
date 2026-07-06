# Dataset, codebook, and survey manager

keprix manages research datasets with variable metadata, missing-value rules, versioned transforms, and exports for PSPP, jamovi, R, and Python.

## Supported inputs

| Format | Notes |
| --- | --- |
| CSV / TSV | Copied to versioned derived storage |
| Excel (`.xlsx`, `.xlsm`) | Requires `openpyxl` |
| JSON | Array or `{records: [...]}` |
| Parquet | Via DuckDB when available |
| SQLite | Table export to CSV |
| Postgres | Query export when `psycopg` installed |
| SPSS `.sav` | Requires `pyreadstat`; labels preserved |
| PSPP `.sps` | Syntax stored; data imported separately |

Original uploads are copied to `datasets/originals/{dataset_id}/` and never mutated.

## Codebook model

Each variable stores:

- Name, label, type, measurement level
- Value labels and missing value codes
- Derived expression and source column
- Validation rules and notes

Codebooks persist at `datasets/codebooks/{dataset_id}/v{N}.json`.

## Versioning and lineage

Derived data lives under `datasets/derived/{dataset_id}/v{N}/data.csv`. Every import or transform appends a lineage step in `datasets/lineage/`.

## Safety

- Original files remain read-only copies.
- Preview endpoints return redacted sample rows (emails and long strings masked).
- Logs avoid printing full private datasets.

## Exports

| Format | Output |
| --- | --- |
| `csv` | Clean CSV with label and name header rows |
| `parquet` | Parquet file (requires `pyarrow`) |
| `json-schema` | JSON schema + variable metadata |
| `pspp` | PSPP syntax with value and missing labels |
| `r` | R script with label attributes |
| `python` | Notebook-ready pandas cell |
| `jamovi` | CSV plus metadata notes markdown |

## API

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/research/datasets/projects/{id}/import` | Import file and create codebook |
| GET | `/api/research/datasets/{id}` | Dataset detail, codebook, lineage |
| GET | `/api/research/datasets/{id}/preview` | Redacted sample rows |
| PUT | `/api/research/datasets/{id}/codebook` | Update codebook |
| POST | `/api/research/datasets/{id}/transform` | Apply versioned transform |
| POST | `/api/research/datasets/{id}/export` | Export clean artifact |
| POST | `/api/research/datasets/{id}/validate` | Validate sample rows |

## Downstream consumers

PSPP, jamovi, R, and Python analysis prompts should read exported artifacts and codebooks from this manager rather than re-implementing import logic. PSPP syntax and runs are handled by [pspp-runner.md](pspp-runner.md).

## Related docs

- [research-workspace-architecture.md](research-workspace-architecture.md)
- [zotero-citation-adapter.md](zotero-citation-adapter.md)
