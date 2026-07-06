# Analytics workspace

The analytics workspace is a Python-backed computational environment for data analysis. Upload a CSV, connect a database, or point at a file in your workspace - then ask the agent to analyse it, generate charts, and summarise findings.

## How it works

The analytics workspace runs Python in a sandboxed subprocess. The agent has access to a pre-installed data science stack:

- `pandas` and `polars` for tabular data
- `matplotlib`, `seaborn`, and `plotly` for charts
- `scipy` and `statsmodels` for statistical analysis
- `scikit-learn` for machine learning
- `duckdb` for SQL queries over files and dataframes

Generated charts are returned as images embedded in the conversation. Code and outputs are shown in a collapsible code block.

## Routes

| Route | Purpose |
| --- | --- |
| `/analytics` | Analytics workspace (data upload, query, charts) |
| `/admin/analytics` | Operator analytics: usage timeline, token spend, user activity |
| Opportunity analytics | Growth loop metrics inside an opportunity workspace |

## Opening the analytics workspace

Navigate to `/analytics` or click the **Analytics** card in the launcher.

You can also start an analytics session from chat with `/analytics` followed by a question.

## Uploading data

Drag a file onto the analytics workspace or use the upload button. Supported formats:

- CSV and TSV
- Excel (`.xlsx`, `.xls`)
- JSON and JSONL
- Parquet
- SQLite database files

Uploaded files are available to the agent as named dataframes. The agent identifies the schema automatically and summarises it before you ask any questions.

## Connecting a database

Connect to a live database for direct querying:

```bash
KEPRIX_ANALYTICS_DB_CONNECTORS=postgres,mysql,sqlite
```

In the UI: **Analytics > Connect database**, select the type, and enter credentials. The connection is scoped to the analytics workspace session.

Supported databases: PostgreSQL, MySQL, SQLite, DuckDB, BigQuery, Snowflake.

## Example queries

Just ask in natural language:

```
Show me the top 10 customers by revenue last quarter
```

```
Plot monthly sales as a bar chart, overlaid with a 3-month rolling average
```

```
Run a linear regression of temperature on ice cream sales
```

```
What percentage of orders have a discount applied?
```

The agent writes and runs the Python code, shows you the code and output, and provides a plain-language interpretation.

## Code transparency

Every chart and analysis result shows the code used to produce it. Click **Show code** on any result to see the exact Python that ran. Copy, edit, and re-run it from the UI.

## Sandboxing

Analytics code runs inside a restricted subprocess:

- File system access limited to the workspace data directory.
- Network access disabled (no outbound requests from analysis code).
- Memory and CPU limits enforced.
- Timeout: `KEPRIX_ANALYTICS_TIMEOUT` seconds (default 60).

## Configuration

```bash
KEPRIX_ANALYTICS_ENABLED=true
KEPRIX_ANALYTICS_TIMEOUT=60          # seconds per code execution
KEPRIX_ANALYTICS_MAX_ROWS=1000000    # rows per uploaded file
KEPRIX_ANALYTICS_MAX_FILE_MB=100     # upload size limit
```

## Saving and exporting results

- **Save chart**: click the download icon on any chart to save as PNG or SVG.
- **Export notebook**: export the full session as a Jupyter notebook (`.ipynb`) with all code cells and outputs.
- **Export report**: generate a Markdown or PDF report summarising the analysis.

## API

```http
POST /api/analytics/sessions                  # create a new analytics session
POST /api/analytics/sessions/{id}/upload      # upload a data file
POST /api/analytics/sessions/{id}/query       # run a natural-language query
GET  /api/analytics/sessions/{id}/results     # list results
GET  /api/analytics/sessions/{id}/export      # export as notebook
```

## Related

- [Deep research](research.md)
- [Self-coding agent](self-coding-agent.md)
- [Evals](evals.md)
- [Playbooks](playbooks.md)
- [RAG pipelines](rag-pipelines.md)
