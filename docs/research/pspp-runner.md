# PSPP CLI runner

keprix generates SPSS-compatible PSPP syntax from dataset codebooks, runs the PSPP CLI when installed, and stores reproducible statistical artifacts.

## Syntax generator

`stats/pspp/syntax.py` builds `.sps` files with:

- `GET FILE` / data import
- `VARIABLE LABELS`
- `VALUE LABELS`
- `MISSING VALUES`
- Analysis procedures: `FREQUENCIES`, `DESCRIPTIVES`, `CROSSTABS`, `T-TEST`, `ONEWAY`, `CORRELATIONS`, `REGRESSION`, `LOGISTIC REGRESSION`

Variable names are sanitized; shell fragments (`;`, `` ` ``, `|`, `$`) are rejected.

External data paths require `approve_external_paths=true`.

## Runner

```text
pspp analysis.sps -o output.html
pspp analysis.sps -o output.odt
pspp analysis.sps -o output.txt
```

`GET /api/research/pspp/status` reports whether PSPP is installed and returns setup instructions when it is not.

If PSPP is missing, keprix still stores the generated syntax artifact with `status=syntax_only`.

## Artifacts

Each run stores under `{workspace}/pspp_runs/{run_id}/`:

| File | Purpose |
| --- | --- |
| `analysis.sps` | Generated syntax |
| `manifest.json` | Trace ID, dataset version, procedures |
| `output.txt` / `.html` / `.odt` | PSPP output when run succeeds |

Parsed tables are returned in `parsed_tables` when output can be read.

Research objects:

- `statistical_output` for syntax generation
- `statistical_output` for run results (`{run_id}-output`)

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/research/pspp/status` | Detect PSPP installation |
| POST | `/api/research/pspp/generate` | Generate syntax from dataset codebook |
| POST | `/api/research/pspp/run` | Execute PSPP or return syntax-only result |

## Safety

- Runs execute inside `{workspace}/pspp_runs/{run_id}/` only.
- No arbitrary shell fragments in generated syntax.
- External paths require explicit approval.
- Original dataset uploads remain untouched (dataset manager originals).

## Related docs

- [dataset-codebook-manager.md](dataset-codebook-manager.md)
- [research-workspace-architecture.md](research-workspace-architecture.md)
