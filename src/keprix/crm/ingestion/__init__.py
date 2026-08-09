"""Shared CRM lead ingestion (Prompt 621)."""

from __future__ import annotations

from keprix.crm.ingestion.canonical import (
    ALIASES,
    CANONICAL_KEYS,
    REFERENCE_HEADERS,
    map_headers,
    normalize_row,
)
from keprix.crm.ingestion.dedup import find_existing, match_key
from keprix.crm.ingestion.export import export_leads, export_leads_csv, export_leads_xlsx
from keprix.crm.ingestion.readers import (
    SUPPORTED_INGEST_SUFFIXES,
    read_bytes,
    read_path,
    read_rows_list,
)
from keprix.crm.ingestion.service import (
    IngestOptions,
    ingest_bytes,
    ingest_channel_attachment,
    ingest_file,
    ingest_row_array,
    ingest_rows,
    preview_rows,
)

__all__ = [
    "ALIASES",
    "CANONICAL_KEYS",
    "REFERENCE_HEADERS",
    "SUPPORTED_INGEST_SUFFIXES",
    "IngestOptions",
    "export_leads",
    "export_leads_csv",
    "export_leads_xlsx",
    "find_existing",
    "ingest_bytes",
    "ingest_channel_attachment",
    "ingest_file",
    "ingest_row_array",
    "ingest_rows",
    "map_headers",
    "match_key",
    "normalize_row",
    "preview_rows",
    "read_bytes",
    "read_path",
    "read_rows_list",
]
