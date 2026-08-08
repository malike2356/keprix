from __future__ import annotations

from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

from keprix.sheet_preprocess import (  # noqa: E402
    BUILTIN_SHEET_TYPES,
    ColumnRole,
    FillProposal,
    SheetLimits,
    SheetPreprocessor,
    SheetSafetyError,
    SheetTypeRegistration,
    apply_proposal,
    build_crm_upsert_plan,
    classify_sheet,
    escape_csv_cell,
    get_sheet_type_registry,
    is_blank_cell,
    load_table_with_inspection,
    register_pack_sheet_type,
    validate_fills,
    write_table,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_column_role_enum_covers_required_roles() -> None:
    required = {
        "identity",
        "metric",
        "enrich_target",
        "pii",
        "ignore",
        "score",
        "stage",
        "contact_email",
        "contact_phone",
        "company_name",
        "url",
    }
    assert required <= {role.value for role in ColumnRole}


def test_builtin_sheet_types_include_property_among_many() -> None:
    assert BUILTIN_SHEET_TYPES == ("generic", "leads", "tenant_list", "property_data")
    assert classify_sheet(["Lead ID", "Contact Email", "Pipeline Stage"]) == "leads"
    assert classify_sheet(["Property Address", "Bedrooms", "Valuation"]) == "property_data"
    assert classify_sheet(["Tenant", "Lease Start", "Rent"]) == "tenant_list"
    assert classify_sheet(["Experiment ID", "Temperature"]) == "generic"


def test_pack_registry_hook_registers_extra_type() -> None:
    registry = get_sheet_type_registry()
    register_pack_sheet_type(
        SheetTypeRegistration(
            sheet_type="clinic_referrals",
            markers=("referral", "clinic", "nhs"),
            pack_id="health",
            description="Pack test type",
        )
    )
    assert "clinic_referrals" in registry.known_types()
    assert classify_sheet(["Referral ID", "Clinic Name", "NHS Number"]) == "clinic_referrals"


def test_auto_propose_is_domain_agnostic_and_does_not_mutate() -> None:
    frame = pd.DataFrame({"Experiment ID": [1], "Temperature": [None], "Outcome": ["pass"]})
    original = frame.copy(deep=True)

    job = SheetPreprocessor().propose(frame, metrics=["Temperature", "Pressure"])

    assert job.proposal.sheet_type == "generic"
    assert job.proposal.columns["Temperature"].role == ColumnRole.METRIC
    assert job.proposal.missing_metrics == ["Pressure"]
    assert job.proposal.mode == "auto_analyse"
    assert frame.equals(original)
    assert job.status == "proposed"


def test_user_schema_and_model_proposals_are_respected() -> None:
    frame = pd.DataFrame({"Organisation": ["Acme"], "Priority": [None]})

    def analyser(payload):
        assert payload["columns"]["Priority"] == "enrich_target"
        assert payload["rules"]["empty_cells_only"] is True
        return {
            "fills": [
                {
                    "row_index": 0,
                    "column": "Priority",
                    "value": "high",
                    "confidence": 0.9,
                    "evidence": "row context",
                }
            ]
        }

    job = SheetPreprocessor(analyser).propose(
        frame,
        user_schema={"Organisation": "company_name", "Priority": "enrich_target"},
    )

    assert frame.loc[0, "Priority"] is None
    assert job.proposal.fills[0].value == "high"
    assert job.proposal.mode == "user_schema"
    assert job.proposal.fills[0].provenance_kind == "model_inferred"


def test_apply_never_overwrites_existing_cells() -> None:
    frame = pd.DataFrame({"Email": [None, "known@example.com", 0, False, "  "]})
    fills = [
        FillProposal(0, "Email", "new@example.com"),
        FillProposal(1, "Email", "overwrite@example.com"),
        FillProposal(2, "Email", "should-skip-zero"),
        FillProposal(3, "Email", "should-skip-false"),
        FillProposal(4, "Email", "from-whitespace"),
    ]

    output, applied, skipped = apply_proposal(frame, fills)

    assert output.loc[0, "Email"] == "new@example.com"
    assert output.loc[1, "Email"] == "known@example.com"
    assert output.loc[2, "Email"] == 0
    assert output.loc[3, "Email"] is False
    assert output.loc[4, "Email"] == "from-whitespace"
    assert applied == 2
    assert skipped == 3


def test_blank_policy_keeps_placeholders_and_formulas() -> None:
    assert is_blank_cell(None)
    assert is_blank_cell("")
    assert is_blank_cell("   ")
    assert not is_blank_cell(0)
    assert not is_blank_cell(False)
    assert not is_blank_cell("n/a")
    assert not is_blank_cell("=A1+1")


def test_fixture_leads_propose_and_crm_plan(tmp_path: Path) -> None:
    path = FIXTURES / "leads.csv"
    frame, inspection = load_table_with_inspection(path)
    assert inspection.content_hash
    assert inspection.delimiter == ","

    def analyser(payload):
        fills = []
        for offset, row in enumerate(payload["rows"]):
            row_index = payload["row_offset"] + offset
            email = row.get("contact_email")
            stage = row.get("stage")
            email_blank = email is None or (isinstance(email, float) and pd.isna(email)) or str(email).strip() == ""
            stage_blank = stage is None or (isinstance(stage, float) and pd.isna(stage)) or str(stage).strip() == ""
            if email_blank:
                # Contact without evidence must become a review issue.
                fills.append(
                    {
                        "row_index": row_index,
                        "column": "contact_email",
                        "value": "guess@example.com",
                        "confidence": 0.4,
                    }
                )
            if stage_blank:
                fills.append(
                    {
                        "row_index": row_index,
                        "column": "stage",
                        "value": "discovered",
                        "confidence": 0.8,
                        "evidence": "default empty stage",
                    }
                )
        return {"fills": fills, "tokens_used": 10}

    preprocessor = SheetPreprocessor(analyser, max_rows=50, batch_size=2)
    job = preprocessor.propose(
        frame,
        content_hash=inspection.content_hash,
        build_crm_plan=True,
    )

    assert job.proposal.sheet_type == "leads"
    assert job.proposal.columns["contact_email"].role == ColumnRole.CONTACT_EMAIL
    assert any(issue.code == "contact_without_evidence" for issue in job.proposal.issues)
    assert all(fill.column != "contact_email" for fill in job.proposal.fills)
    assert job.crm_upsert_plan is not None
    assert any(row.entity_type == "Lead" for row in job.crm_upsert_plan.rows)
    assert frame.isna().sum().sum() >= 1  # source unchanged

    out = tmp_path / "leads-out.csv"
    applied = preprocessor.apply(frame, job, output_path=out)
    assert applied.status == "applied"
    assert applied.output_hash
    text = out.read_text(encoding="utf-8")
    assert "discovered" in text


def test_fixture_generic_formula_safety_and_csv_escape(tmp_path: Path) -> None:
    path = FIXTURES / "generic.csv"
    frame, inspection = load_table_with_inspection(path)
    assert inspection.formula_cells >= 1
    assert any("never evaluated" in warning.lower() or "formula" in warning.lower()
               for warning in inspection.warnings)

    # Formula cell must not be treated as blank / overwrite target.
    formula_row = next(
        i for i, value in enumerate(frame["Notes"].tolist()) if isinstance(value, str) and value.startswith("=")
    )
    fills = [FillProposal(formula_row, "Notes", "overwrite-formula")]
    output, applied, skipped = apply_proposal(frame, fills)
    assert applied == 0
    assert skipped == 1
    assert str(output.iloc[formula_row]["Notes"]).startswith("=")

    out = tmp_path / "generic-out.csv"
    write_table(pd.DataFrame({"Payload": ["=CMD()"]}), out)
    assert out.read_text(encoding="utf-8").splitlines()[1].startswith("'=")


def test_validate_fills_dedupes_and_bounds_columns() -> None:
    frame = pd.DataFrame({"Priority": [None], "Id": ["1"]})
    from keprix.sheet_preprocess import analyse_columns

    columns = analyse_columns(
        frame.columns,
        {"Priority": "enrich_target", "Id": "identity"},
    )
    accepted, issues = validate_fills(
        [
            {"row_index": 0, "column": "Priority", "value": "a", "confidence": 0.9},
            {"row_index": 0, "column": "Priority", "value": "b", "confidence": 0.9},
            {"row_index": 0, "column": "Id", "value": "x", "confidence": 0.9},
        ],
        columns=columns,
        frame=frame,
    )
    assert len(accepted) == 1
    assert any(issue.code == "duplicate_fill" for issue in issues)
    assert any(issue.code == "column_not_fillable" for issue in issues)


def test_resumable_batches_and_cancellation() -> None:
    frame = pd.DataFrame(
        {
            "company_name": [f"Co{i}" for i in range(6)],
            "stage": [None] * 6,
        }
    )
    calls: list[int] = []

    def analyser(payload):
        calls.append(payload["row_offset"])
        return {
            "fills": [
                {
                    "row_index": payload["row_offset"],
                    "column": "stage",
                    "value": "discovered",
                    "confidence": 0.7,
                    "evidence": "batch",
                }
            ],
            "tokens_used": 5,
        }

    preprocessor = SheetPreprocessor(analyser, max_rows=6, batch_size=2)
    first = preprocessor.propose(frame)
    assert first.proposal.checkpoint.batches_completed == 3
    assert len(calls) == 3

    calls.clear()
    preprocessor2 = SheetPreprocessor(analyser, max_rows=6, batch_size=2)
    # Simulate resume after first batch.
    first.proposal.fills = first.proposal.fills[:1]
    first.proposal.checkpoint.next_row = 2
    first.proposal.checkpoint.batches_completed = 1
    first.status = "partial"
    resumed = preprocessor2.propose(frame, resume_from=first)
    assert calls == [2, 4]
    assert resumed.proposal.checkpoint.next_row == 6

    canceller = SheetPreprocessor(analyser, max_rows=6, batch_size=2)
    canceller.request_cancel()
    cancelled = canceller.propose(frame)
    assert cancelled.cancelled or cancelled.status == "cancelled"


def test_file_limits_reject_oversized(tmp_path: Path) -> None:
    path = tmp_path / "big.csv"
    path.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(SheetSafetyError, match="size limit"):
        load_table_with_inspection(path, limits=SheetLimits(max_bytes=4))


def test_escape_csv_cell_prefixes_injection_chars() -> None:
    assert escape_csv_cell("=1+1") == "'=1+1"
    assert escape_csv_cell("+cmd") == "'+cmd"
    assert escape_csv_cell("safe") == "safe"


def test_crm_upsert_plan_is_plan_only() -> None:
    frame = pd.DataFrame(
        {
            "lead_id": ["L1"],
            "company_name": ["Acme"],
            "contact_email": ["a@example.com"],
            "stage": ["discovered"],
        }
    )
    job = SheetPreprocessor().propose(
        frame,
        user_schema={
            "lead_id": "identity",
            "company_name": "company_name",
            "contact_email": "contact_email",
            "stage": "stage",
        },
        build_crm_plan=True,
    )
    plan = job.crm_upsert_plan
    assert plan is not None
    assert {row.entity_type for row in plan.rows} >= {"Account", "Lead", "Contact"}
    # Rebuilding via helper returns a new plan object; still no CRM side effects.
    again = build_crm_upsert_plan(frame, job.proposal)
    assert again.rows
