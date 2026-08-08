"""Domain-agnostic spreadsheet analysis and enrichment."""

from keprix.sheet_preprocess.crm_plan import build_crm_upsert_plan
from keprix.sheet_preprocess.models import (
    ColumnRole,
    ColumnSpec,
    CrmUpsertPlan,
    CrmUpsertRow,
    EnrichmentJob,
    FillProposal,
    ReviewIssue,
    SheetInspection,
    SheetProposal,
)
from keprix.sheet_preprocess.processor import (
    SheetPreprocessor,
    analyse_columns,
    apply_proposal,
    classify_sheet,
    count_blank_cells,
    load_table,
    load_table_with_inspection,
    write_table,
)
from keprix.sheet_preprocess.registry import (
    BUILTIN_SHEET_TYPES,
    SheetTypeRegistration,
    SheetTypeRegistry,
    get_sheet_type_registry,
    register_pack_classifier,
    register_pack_schema_provider,
    register_pack_sheet_type,
)
from keprix.sheet_preprocess.safety import (
    SheetLimits,
    SheetSafetyError,
    content_hash_file,
    escape_csv_cell,
    is_blank_cell,
    write_csv_safe,
)
from keprix.sheet_preprocess.validation import validate_fills

__all__ = [
    "BUILTIN_SHEET_TYPES",
    "ColumnRole",
    "ColumnSpec",
    "CrmUpsertPlan",
    "CrmUpsertRow",
    "EnrichmentJob",
    "FillProposal",
    "ReviewIssue",
    "SheetInspection",
    "SheetLimits",
    "SheetPreprocessor",
    "SheetProposal",
    "SheetSafetyError",
    "SheetTypeRegistration",
    "SheetTypeRegistry",
    "analyse_columns",
    "apply_proposal",
    "build_crm_upsert_plan",
    "classify_sheet",
    "content_hash_file",
    "count_blank_cells",
    "escape_csv_cell",
    "get_sheet_type_registry",
    "is_blank_cell",
    "load_table",
    "load_table_with_inspection",
    "register_pack_classifier",
    "register_pack_schema_provider",
    "register_pack_sheet_type",
    "validate_fills",
    "write_csv_safe",
    "write_table",
]
