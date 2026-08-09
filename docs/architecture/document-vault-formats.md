# Document Vault format engines (Prompt 647)

**Status:** REAL for CE markdown/html/text/csv/pdf; PARTIAL for xlsx/docx/ods; blocked_optional for pptx/odt/rtf

## Capability surface

`GET /api/document-vault/formats` returns the client matrix (web, desktop, TUI, agents).

## Rules

1. Import keeps the original as `binary_upload` and creates a derived editable item.
2. Generated PDF is a sibling `pdf` artifact with `source_item_id` + `source_revision`; source checksum never changes.
3. Lossy or unavailable converters return explicit `warnings` / `not_configured` and do not write over the source.
4. MIME sniffing rejects spoofed types; OOXML macros and executable archive members are rejected.
5. Size and archive bomb limits apply before conversion.

## Engines

| Module | Role |
| --- | --- |
| `document_vault/formats/registry.py` | Capability registry |
| `document_vault/formats/safety.py` | Sniff, limits, macros, HTML sanitize |
| `document_vault/formats/engines.py` | Import/export/PDF converters |
| Reuse | `keprix.export.renderer`, `keprix.export.pdf_engine`, `workspace.pdf_export` |

## Tests

```bash
./.venv/bin/python -m pytest tests/document_vault/test_formats.py -q
```
