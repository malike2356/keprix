"""Standalone lead/outreach conformance (Prompt 620).

Documents current readiness honestly. This suite must NOT report
standalone_outreach_ready=True until Prompt 628 closes the series.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keprix.crm.models import FORWARD_STAGES, TERMINAL_STAGES, CrmStage

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "docs/architecture/standalone-lead-outreach-capability-matrix.md"
CONTRACT_DOC = ROOT / "docs/architecture/standalone-lead-outreach-contract.md"
CONTRACT_SCHEMA = ROOT / "schemas/standalone-lead-outreach/contract.schema.json"

# Known gaps that must remain visible until later prompts close them.
KNOWN_GAPS: dict[str, str] = {
    "live_email_send": "PARTIAL: dry-run default / incomplete account bind (625)",
    "provider_events": "MISSING: no ESP webhook normalizer (625)",
    "automatic_mailbox_scan": "PARTIAL: stub/cron prompt only (626)",
    "channel_attachment_import": "SIMULATED: email_ingest stub (627)",
}

# Prompt 624 closed campaign_scheduler; do not list it as an open gap.
CLOSED_CAPABILITIES: dict[str, str] = {
    "campaign_scheduler": "REAL: claim-lease process-due + Soft Wall park (624)",
}


def test_baseline_docs_exist() -> None:
    assert MATRIX.is_file(), "capability matrix missing"
    assert CONTRACT_DOC.is_file(), "contract doc missing"
    assert CONTRACT_SCHEMA.is_file(), "contract schema missing"
    text = MATRIX.read_text(encoding="utf-8")
    assert "LIVE email send" in text or "Live email send" in text
    assert "Provider events" in text
    assert "Do not mark complete from UI alone" in text or "UI presence" in text


def test_contract_schema_version_and_readiness_flag() -> None:
    schema = json.loads(CONTRACT_SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["contract_version"]["const"] == "1.0.0"
    assert "standalone_outreach_ready" in schema["properties"]
    # Programme is not complete at Prompt 620.
    assert schema["properties"]["standalone_outreach_ready"].get("description")


def test_crm_stages_are_contract_source_of_truth() -> None:
    forward = list(FORWARD_STAGES)
    assert forward[0] == CrmStage.DISCOVERED
    assert forward[-1] == CrmStage.PAYING
    assert CrmStage.SUPPRESSED in TERMINAL_STAGES
    assert "new" not in forward  # outreach label, not CRM SoT


def test_reuse_packages_present() -> None:
    for rel in (
        "src/keprix/crm",
        "src/keprix/outreach",
        "src/keprix/discovery",
        "src/keprix/sheet_preprocess",
        "src/keprix/crm/soft_wall.py",
    ):
        assert (ROOT / rel).exists(), f"reuse target missing: {rel}"


def test_known_gaps_catalogued_and_not_false_ready() -> None:
    """Gap catalog must stay non-empty until 628; readiness stays false."""
    assert KNOWN_GAPS, "gap catalog emptied prematurely"
    assert "campaign_scheduler" not in KNOWN_GAPS
    assert CLOSED_CAPABILITIES.get("campaign_scheduler", "").startswith("REAL")
    readiness = False
    for key, note in KNOWN_GAPS.items():
        assert note, key
        assert any(tag in note for tag in ("MISSING", "PARTIAL", "SIMULATED")), note
    assert readiness is False, "do not claim standalone_outreach_ready at Prompt 620"


def test_scheduler_docs_and_module_exist() -> None:
    sched_doc = ROOT / "docs/architecture/standalone-lead-outreach-scheduler.md"
    assert sched_doc.is_file()
    assert (ROOT / "src/keprix/outreach/scheduler.py").is_file()
    text = MATRIX.read_text(encoding="utf-8")
    assert "claim-lease" in text or "claim_due" in text or "Durable claim" in text


def test_matrix_lists_series_build_order() -> None:
    text = MATRIX.read_text(encoding="utf-8")
    for prompt in ("620", "621", "622", "623", "624", "625", "626", "627", "628"):
        assert prompt in text, f"build order missing {prompt}"


@pytest.mark.parametrize(
    "path",
    [
        "frontend/src/app/(workspace)/crm/page.tsx",
        "frontend/src/app/(workspace)/outreach/page.tsx",
        "src/keprix/tools/crm_tools.py",
        "src/keprix/tools/outreach_tools.py",
    ],
)
def test_operator_and_tool_surfaces_exist(path: str) -> None:
    assert (ROOT / path).is_file()
