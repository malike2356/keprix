"""Models shared by spreadsheet analysis, review, and apply flows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class ColumnRole(StrEnum):
    IDENTITY = "identity"
    METRIC = "metric"
    ENRICH_TARGET = "enrich_target"
    PII = "pii"
    IGNORE = "ignore"
    SCORE = "score"
    STAGE = "stage"
    CONTACT_EMAIL = "contact_email"
    CONTACT_PHONE = "contact_phone"
    COMPANY_NAME = "company_name"
    URL = "url"


class ProvenanceKind(StrEnum):
    OBSERVED = "observed"
    USER_SUPPLIED = "user_supplied"
    DERIVED = "derived"
    MODEL_INFERRED = "model_inferred"
    VERIFIED = "verified"


class IssueSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


MAPPING_VERSION = "sheet_preprocess.v1"


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    role: ColumnRole
    metric: str | None = None
    data_type: str = "text"
    description: str = ""
    confidence: float = 1.0
    source: str = "user"
    units: str | None = None
    currency: str | None = None
    timezone: str | None = None
    allowed_values: tuple[str, ...] = ()
    validation: str | None = None
    required: bool = False
    unique_key: bool = False
    metric_formula: str | None = None
    pii_class: str | None = None


@dataclass(frozen=True)
class FillProposal:
    row_index: int
    column: str
    value: Any
    confidence: float | None = None
    source: str = "model"
    evidence: str = ""
    provenance_kind: str = ProvenanceKind.MODEL_INFERRED.value
    adapter: str = "sheet_preprocess"
    policy_version: str = MAPPING_VERSION
    observed_at: str | None = None
    source_field: str | None = None
    verification_state: str = "unverified"


@dataclass(frozen=True)
class ReviewIssue:
    code: str
    message: str
    severity: str = IssueSeverity.WARNING.value
    row_index: int | None = None
    column: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchCheckpoint:
    next_row: int = 0
    batches_completed: int = 0
    tokens_used: int = 0
    cancelled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SheetInspection:
    path: str
    content_hash: str
    size_bytes: int
    format: str
    worksheets: list[str] = field(default_factory=list)
    selected_worksheet: str | int | None = None
    header_row: int = 0
    row_count: int = 0
    column_count: int = 0
    delimiter: str | None = None
    encoding: str | None = None
    flattened_export: bool = False
    warnings: list[str] = field(default_factory=list)
    formula_cells: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SheetProposal:
    sheet_type: str
    columns: dict[str, ColumnSpec]
    fills: list[FillProposal] = field(default_factory=list)
    missing_metrics: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    issues: list[ReviewIssue] = field(default_factory=list)
    row_count: int = 0
    blank_cells: int = 0
    analysed_rows: int = 0
    mode: str = "auto_analyse"
    mapping_version: str = MAPPING_VERSION
    content_hash: str | None = None
    selected_worksheet: str | int | None = None
    header_row: int = 0
    flattened_export: bool = False
    checkpoint: BatchCheckpoint = field(default_factory=BatchCheckpoint)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CrmUpsertRow:
    entity_type: str
    action: str
    fields: dict[str, Any]
    row_index: int
    identity_keys: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CrmUpsertPlan:
    """Plan-only CRM write description. Does not mutate CRM stores."""

    sheet_type: str
    rows: list[CrmUpsertRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    mapping_version: str = MAPPING_VERSION
    source_content_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EnrichmentJob:
    proposal: SheetProposal
    status: str = "proposed"
    cells_filled: int = 0
    cells_skipped: int = 0
    output_path: str | None = None
    output_hash: str | None = None
    errors: list[str] = field(default_factory=list)
    crm_upsert_plan: CrmUpsertPlan | None = None
    cancelled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
