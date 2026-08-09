"""Keprix agent tools: CRM lead spreadsheet ingestion (Prompt 621)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.registry import registry

from keprix.crm.store import get_crm_store

TOOLSET = "crm"


def check_crm_ingest_requirements() -> bool:
    return True


def _ok(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _err(message: str, **extra: Any) -> str:
    return json.dumps({"error": message, **extra}, ensure_ascii=False)


def _ws(args: dict[str, Any]) -> str | None:
    ws = str(args.get("workspace_id") or "").strip()
    return ws or None


def crm_ingest_preview(args: dict[str, Any]) -> str:
    ws = _ws(args)
    if not ws:
        return _err("workspace_id is required")
    try:
        from keprix.crm.ingestion.readers import read_path, read_rows_list
        from keprix.crm.ingestion.service import preview_rows
        from keprix.sheet_preprocess.safety import SheetSafetyError

        rows = args.get("rows")
        path = args.get("path") or args.get("file")
        if rows is not None:
            loaded = read_rows_list(list(rows))
        elif path:
            loaded = read_path(str(path))
        else:
            return _err("path or rows is required")
        result = preview_rows(loaded["rows"], limit=int(args.get("limit") or 20))
        result["workspace_id"] = ws
        result["format"] = loaded.get("format")
        result["warnings"] = loaded.get("warnings") or []
        return _ok(result)
    except SheetSafetyError as exc:
        return _err(str(exc), error_code="unsupported_format")
    except Exception as exc:
        return _err(str(exc))


def crm_ingest_import(args: dict[str, Any]) -> str:
    ws = _ws(args)
    if not ws:
        return _err("workspace_id is required")
    try:
        from keprix.crm.ingestion.service import (
            IngestOptions,
            ingest_file,
            ingest_row_array,
        )
        from keprix.sheet_preprocess.safety import SheetSafetyError

        options = IngestOptions(
            overwrite=bool(args.get("overwrite")),
            source_type=str(args.get("source_type") or "spreadsheet"),
            source_name=args.get("source_name"),
            source_url=args.get("source_url"),
            actor_id=str(args.get("actor_id") or args.get("user_id") or "agent"),
            actor_type="agent",
            domain_pack=str(args.get("domain_pack") or "generic"),
            dry_run=bool(args.get("dry_run")),
        )
        rows = args.get("rows")
        path = args.get("path") or args.get("file")
        if rows is not None:
            result = ingest_row_array(ws, list(rows), options=options)
        elif path:
            if not options.source_name:
                options.source_name = Path(str(path)).name
            result = ingest_file(ws, str(path), options=options)
        else:
            return _err("path or rows is required")
        result["workspace_id"] = ws
        return _ok(result)
    except SheetSafetyError as exc:
        return _err(str(exc), error_code="unsupported_format")
    except Exception as exc:
        return _err(str(exc))


def crm_leads_export(args: dict[str, Any]) -> str:
    ws = _ws(args)
    if not ws:
        return _err("workspace_id is required")
    path = args.get("path") or args.get("file")
    if not path:
        return _err("path is required")
    try:
        from keprix.crm.ingestion.export import export_leads

        store = get_crm_store()
        leads = store.list_leads(ws, limit=int(args.get("limit") or 10_000))
        fmt = str(args.get("format") or "xlsx")
        out = export_leads(
            leads,
            path,
            format=fmt,
            flatten_custom=bool(args.get("flatten_custom")),
        )
        return _ok({"workspace_id": ws, "path": str(out), "count": len(leads), "format": fmt})
    except Exception as exc:
        return _err(str(exc))


def _ws_props(**extra: Any) -> dict[str, Any]:
    props = {"workspace_id": {"type": "string"}}
    props.update(extra)
    return props


registry.register(
    name="crm_ingest_preview",
    toolset=TOOLSET,
    schema={
        "name": "crm_ingest_preview",
        "description": "Preview spreadsheet/row mapping onto the canonical SEO lead schema.",
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                path={"type": "string"},
                file={"type": "string"},
                rows={"type": "array"},
                limit={"type": "integer"},
            ),
            "required": ["workspace_id"],
        },
    },
    handler=crm_ingest_preview,
    check_fn=check_crm_ingest_requirements,
)

registry.register(
    name="crm_ingest_import",
    toolset=TOOLSET,
    schema={
        "name": "crm_ingest_import",
        "description": "Import leads from CSV/TSV/XLS/XLSX/ODS or a normalized row array.",
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                path={"type": "string"},
                file={"type": "string"},
                rows={"type": "array"},
                overwrite={"type": "boolean"},
                dry_run={"type": "boolean"},
                source_type={"type": "string"},
                source_name={"type": "string"},
                source_url={"type": "string"},
                domain_pack={"type": "string"},
                actor_id={"type": "string"},
            ),
            "required": ["workspace_id"],
        },
    },
    handler=crm_ingest_import,
    check_fn=check_crm_ingest_requirements,
)

registry.register(
    name="crm_leads_export",
    toolset=TOOLSET,
    schema={
        "name": "crm_leads_export",
        "description": "Export workspace CRM leads to Excel (default) or CSV.",
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                path={"type": "string"},
                file={"type": "string"},
                format={"type": "string"},
                flatten_custom={"type": "boolean"},
                limit={"type": "integer"},
            ),
            "required": ["workspace_id", "path"],
        },
    },
    handler=crm_leads_export,
    check_fn=check_crm_ingest_requirements,
)
