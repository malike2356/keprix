"""Customer Concierge v1 contract conformance tests (Prompt 629)."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from keprix.customer_concierge.capability_health import (
    concierge_feature_flags,
    evaluate_capability_health,
)
from keprix.customer_concierge.contract_paths import contract_root, fixtures_dir, load_manifest
from keprix.customer_concierge.contract_schema import (
    assert_mandatory_tenant_and_actor,
    parse_domain_wrapper,
    parse_event_envelope,
    parse_readiness_report,
    validate_fixture_file,
)
from keprix.customer_concierge.contract_types import CUSTOMER_CONCIERGE_CONTRACT_VERSION
from keprix.customer_concierge.scope import filter_rows_for_workspace, resolve_scope

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "src/keprix/customer_concierge"
AUDIT = ROOT / "docs/architecture/customer-concierge-v1-baseline-audit.md"
MATRIX = ROOT / "docs/architecture/customer-concierge-capability-matrix.md"


def test_manifest_version_and_no_runtime_dependency() -> None:
    manifest = load_manifest()
    assert manifest["version"] == CUSTOMER_CONCIERGE_CONTRACT_VERSION
    assert manifest["runtimeDependency"] == "none"
    assert "keprix" in manifest.get("products", [])


def test_vendored_contract_exists() -> None:
    root = contract_root()
    assert (root / "contract.json").is_file()
    assert (root / "schemas" / "domain-objects.schema.json").is_file()
    assert fixtures_dir().is_dir()


def test_all_synthetic_fixtures_validate() -> None:
    files = sorted(
        p.name for p in fixtures_dir().glob("*.json") if p.name != "MANIFEST.json"
    )
    assert len(files) >= 8
    for name in files:
        data = json.loads((fixtures_dir() / name).read_text(encoding="utf-8"))
        parsed = validate_fixture_file(name, data)
        if name.startswith("provider-result-") and "not-configured" in name:
            assert parsed.ok is False
            assert parsed.status == "not_configured"
        if name.startswith("readiness-") and "not-configured" in name:
            assert parsed.ready is False
            for feature in parsed.features.model_dump().values():
                assert feature["status"] == "not_configured"


def test_rejects_missing_workspace_id() -> None:
    data = json.loads((fixtures_dir() / "event-conversation-started.json").read_text(encoding="utf-8"))
    del data["workspaceId"]
    with pytest.raises(ValidationError):
        parse_event_envelope(data)


def test_rejects_missing_actor_type() -> None:
    data = json.loads((fixtures_dir() / "domain-booking-held.json").read_text(encoding="utf-8"))
    del data["object"]["actorType"]
    with pytest.raises((ValidationError, ValueError)):
        parsed = parse_domain_wrapper(data)
        assert_mandatory_tenant_and_actor(parsed.object.model_dump())


def test_scope_maps_tenant_alias_and_filters_rows() -> None:
    scope = resolve_scope(tenant_id="ws_a", user_id="op1", persona_id="front")
    assert scope.workspace_id == "ws_a"
    assert scope.tenant_id == "ws_a"
    assert scope.user_id == "op1"
    rows = [
        {"workspaceId": "ws_a", "id": "1"},
        {"workspaceId": "ws_b", "id": "2"},
        {"object": {"workspaceId": "ws_a", "actorType": "audience"}},
    ]
    filtered = filter_rows_for_workspace(rows, "ws_a")
    assert len(filtered) == 2


def test_capability_health_honest_without_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "ZOOM_CLIENT_ID",
        "ZOOM_CLIENT_SECRET",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "SENDGRID_API_KEY",
        "MAILGUN_API_KEY",
        "SMTP_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    report = evaluate_capability_health(workspace_id="ws_ce", persona_id="default")
    assert report["contractVersion"] == CUSTOMER_CONCIERGE_CONTRACT_VERSION
    assert report["ready"] is False
    assert report["features"]["zoom"]["status"] == "not_configured"
    assert report["features"]["microsoftCalendar"]["status"] == "not_configured"
    assert "calendar_invitation_projection" not in report["gaps"]
    assert "durable_notification_delivery" not in report["gaps"]
    assert "zoom_meeting_create" not in report["gaps"]
    assert "microsoft_calendar_live_oauth_store" in report["gaps"]
    assert report["canonicalBookingService"] == "keprix.vical.saga.book_with_saga"
    assert report["persistenceMode"] in {"sqlite", "postgres"}


def test_feature_flags_can_disable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_CONCIERGE_ZOOM_ENABLED", "0")
    flags = concierge_feature_flags()
    assert flags["zoom"] is False
    report = evaluate_capability_health(workspace_id="ws_ce")
    assert report["features"]["zoom"]["status"] == "disabled"


def test_gap_report_and_matrix_exist_and_name_gaps() -> None:
    assert AUDIT.is_file()
    assert MATRIX.is_file()
    text = AUDIT.read_text(encoding="utf-8")
    for needle in (
        "conferencing.py",
        "notifications.py",
        "support/routes.py",
        "zoom_meeting_create",
        "durable_notification_delivery",
        "external_customer_support_api",
        "CARINA",
    ):
        assert needle.lower() in text.lower()
    matrix = MATRIX.read_text(encoding="utf-8")
    assert "MISSING" in matrix
    assert "zoom" in matrix.lower()


def test_package_has_no_carina_imports() -> None:
    offenders: list[str] = []
    for path in PKG.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "carina" or alias.name.startswith("carina."):
                        offenders.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod == "carina" or mod.startswith("carina."):
                    offenders.append(f"{path.name}: from {mod}")
    assert offenders == []


def test_readiness_fixture_via_helper() -> None:
    data = json.loads((fixtures_dir() / "readiness-all-not-configured.json").read_text(encoding="utf-8"))
    report = parse_readiness_report(data)
    assert "zoom" in report.blockers
    assert report.features.microsoftCalendar.status == "not_configured"
