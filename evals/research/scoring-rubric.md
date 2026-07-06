# Research Workspace Eval Scoring Rubric

Each category scores 0 (fail), 1 (partial), or 2 (pass). Target: 2 on all categories before release.

## Categories

| Category | Pass criteria |
| --- | --- |
| Citation accuracy | BibTeX and Better BibTeX fixtures parse to stable keys, authors, and DOI fields |
| Source attribution | Claims without a registered source are rejected by evidence service |
| Claim-to-evidence linking | Approved claims appear in evidence bundle members |
| Dataset import correctness | CSV fixture imports with expected columns and row counts |
| Codebook preservation | Variable labels, value labels, and missing codes survive import |
| PSPP syntax generation | Generated syntax contains required procedure blocks and sanitized identifiers |
| Statistical result preservation | Mock PSPP output parses into tables without losing row values |
| Report bibliography generation | Report export includes bibliography section for cited records |
| Obsidian note safety | Notes reject script injection, javascript links, and path traversal wikilinks |
| Reproducibility bundle export | Evidence bundle records trace ID, members, and provenance chain |

## Release gate

- Eval runner exits 0 only when every category scores 2.
- Integration smoke test must pass in CI.
- Reports must not ship uncited factual claims unless explicitly marked with an allowed opinion marker.
