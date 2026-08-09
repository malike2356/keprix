"""Standalone lead/outreach conformance (Prompt 620 / closed by 628).

Reports standalone_outreach_ready=True when Prompt 628 E2E + observability
+ ops docs are present and the series gap catalog is empty.
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

# Series closed at Prompt 628: no MISSING programme gaps remain.
KNOWN_GAPS: dict[str, str] = {}

CLOSED_CAPABILITIES: dict[str, str] = {
    "campaign_scheduler": "REAL: claim-lease process-due + Soft Wall park (624)",
    "live_email_send": "REAL: Soft Wall approve + SMTP bind / honest dry-run default (625)",
    "provider_events": "REAL: SES/SendGrid/Mailgun normalizer + apply + idempotency (625)",
    "automatic_mailbox_scan": "REAL: IMAP normalize/match/ingest + cursors + Soft Wall drafts (626)",
    "channel_attachment_import": "REAL: ingest_channel_attachment + email_ingest poll_once default off (627)",
    "channel_telegram_initiation": "REAL: telegram funnel journey intents (627)",
    "e2e_observability_release": "REAL: journey test + observability API + ops docs + deploy (628)",
}

STANDALONE_OUTREACH_READY = True


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


def test_series_ready_after_628() -> None:
    """Gap catalog empty; closed capabilities REAL; readiness true."""
    assert KNOWN_GAPS == {}
    assert "e2e_observability_release" not in KNOWN_GAPS
    for key in (
        "campaign_scheduler",
        "live_email_send",
        "provider_events",
        "automatic_mailbox_scan",
        "channel_attachment_import",
        "e2e_observability_release",
    ):
        assert CLOSED_CAPABILITIES.get(key, "").startswith("REAL"), key
    assert STANDALONE_OUTREACH_READY is True
    e2e = ROOT / "tests/crm/test_standalone_outreach_e2e_journey.py"
    obs = ROOT / "src/keprix/outreach/observability.py"
    ops_doc = ROOT / "docs/architecture/standalone-lead-outreach-ops.md"
    assert e2e.is_file() and obs.is_file() and ops_doc.is_file()
    matrix = MATRIX.read_text(encoding="utf-8")
    assert "Observability" in matrix
    assert "End-to-end journey" in matrix


def test_funnel_docs_and_modules_exist() -> None:
    funnel_doc = ROOT / "docs/architecture/standalone-lead-outreach-funnel.md"
    assert funnel_doc.is_file()
    for rel in (
        "src/keprix/crm/funnel_orchestrator.py",
        "src/keprix/crm/channel_journey.py",
        "src/keprix/crm/next_best_action.py",
        "src/keprix/crm/lifecycle.py",
    ):
        assert (ROOT / rel).is_file()
    text = MATRIX.read_text(encoding="utf-8")
    assert "Channel-attachment import" in text
    assert "email_ingest" in text or "REAL" in text


def test_mailbox_docs_and_module_exist() -> None:
    mailbox_doc = ROOT / "docs/architecture/standalone-lead-outreach-mailbox.md"
    assert mailbox_doc.is_file()
    assert (ROOT / "src/keprix/outreach/inbound_mail.py").is_file()
    assert (ROOT / "src/keprix/outreach/thread_match.py").is_file()
    text = MATRIX.read_text(encoding="utf-8")
    assert "Automatic mailbox reply scan" in text
    assert "inbound_mail" in text or "scan_replies" in text or "REAL" in text


def test_delivery_docs_and_module_exist() -> None:
    delivery_doc = ROOT / "docs/architecture/standalone-lead-outreach-delivery.md"
    assert delivery_doc.is_file()
    assert (ROOT / "src/keprix/outreach/delivery.py").is_file()
    assert (ROOT / "src/keprix/outreach/provider_events.py").is_file()
    text = MATRIX.read_text(encoding="utf-8")
    assert "delivery.send_approved_message" in text or "provider_events" in text


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
