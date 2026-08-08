"""Foundation acceptance tests for keprix-sidecar-foundation (KSF-00..04)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.product_sidecar.auth import get_token_service, grants_for_product
from keprix.product_sidecar.conformance import ConformanceFailure, run_foundation_conformance
from keprix.product_sidecar.connector import ConnectorDenied, FakeProductConnector, assert_safe_url
from keprix.product_sidecar.fixtures import FIXTURE_PRODUCT_KEYS, build_fixture_pack
from keprix.product_sidecar.openapi_contract import runtime_agrees_with_openapi
from keprix.product_sidecar.provision import (
    disable_product,
    plan_provision,
    provision_product,
    rollback_product,
    upgrade_product,
)
from keprix.product_sidecar.registry import (
    PackValidationError,
    get_product_pack_registry,
)
from keprix.product_sidecar.routes import router
from keprix.product_sidecar.state import (
    JobStore,
    get_event_store,
    get_job_store,
    get_memory_store,
    reset_all_sidecar_state_for_tests,
)


@pytest.fixture(autouse=True)
def _reset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_PRODUCT_SIDECAR_TOKEN_SECRET", "test-secret")
    monkeypatch.setenv("CARINA_KEPRIX_SHARED_TOKEN", "test-carina-keprix-shared")
    reset_all_sidecar_state_for_tests()
    get_token_service().reset_for_tests()
    get_product_pack_registry().reset_for_tests(install_fixtures=True)


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _auth(token: str = "test-carina-keprix-shared") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Correlation-ID": "ksf-corr"}


def test_five_fixture_packs_no_namespace_collision() -> None:
    registry = get_product_pack_registry()
    keys = {p["product_key"] for p in registry.list_packs()}
    for key in FIXTURE_PRODUCT_KEYS:
        assert key in keys
    namespaces = [p["memory_namespace"] for p in registry.list_packs()]
    assert len(namespaces) == len(set(namespaces))


def test_failed_pack_activation_rolls_back_atomically() -> None:
    registry = get_product_pack_registry()
    before = registry.require("abbis").checksum
    with pytest.raises(PackValidationError):
        registry.install(build_fixture_pack("abbis", corrupt=True))
    assert registry.require("abbis").checksum == before


def test_disable_kill_switch_blocks_invoke_immediately(client: TestClient) -> None:
    registry = get_product_pack_registry()
    registry.disable("petraclus")
    token, _ = get_token_service().mint(
        product="petraclus",
        workspace_id="ws1",
        actor_id="u",
        grants=grants_for_product("petraclus"),
        purpose="t",
    )
    res = client.post(
        "/v1/products/petraclus/invoke",
        headers=_auth(token),
        json={"node": "pack.ping", "workspace_id": "ws1", "input": {}},
    )
    assert res.status_code == 503
    assert res.json()["detail"]["code"] == "pack_disabled"


def test_cross_product_composition_fails_closed() -> None:
    registry = get_product_pack_registry()
    with pytest.raises(PermissionError):
        registry.compose_nodes("abbis", "clinicom")


def test_fixture_invoke_typed_result(client: TestClient) -> None:
    token, _ = get_token_service().mint(
        product="xeclone",
        workspace_id="ws1",
        actor_id="u",
        grants=grants_for_product("xeclone"),
        purpose="t",
    )
    res = client.post(
        "/v1/products/xeclone/invoke",
        headers=_auth(token),
        json={"node": "pack.ping", "workspace_id": "ws1", "input": {"message": "hi"}},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["result"]["product"] == "xeclone"
    assert body["result"]["message"] == "hi"


def test_unknown_disabled_unauthorised_no_handler(client: TestClient) -> None:
    token, _ = get_token_service().mint(
        product="petraclus",
        workspace_id="ws1",
        actor_id="u",
        grants=frozenset({"node:pack.ping", "petraclus:ping"}),
        purpose="t",
    )
    unknown = client.post(
        "/v1/products/petraclus/invoke",
        headers=_auth(token),
        json={"node": "shell.exec", "workspace_id": "ws1", "input": {}},
    )
    assert unknown.status_code == 404

    weak, _ = get_token_service().mint(
        product="petraclus",
        workspace_id="ws1",
        actor_id="u",
        grants=frozenset({"unrelated"}),
        purpose="t",
    )
    denied = client.post(
        "/v1/products/petraclus/invoke",
        headers=_auth(weak),
        json={"node": "pack.ping", "workspace_id": "ws1", "input": {}},
    )
    assert denied.status_code == 403


def test_jobs_survive_restart_and_stream_cursor(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    job = get_job_store().create(
        product="abbis",
        workspace_id="ws1",
        node_key="pack.ping",
        input_payload={"message": "x"},
        idempotency_key="restart-1",
    )
    get_job_store().complete(job["job_id"], {"ok": True})

    # Simulate process restart by constructing a new durable store against same dir
    restarted = JobStore(durable=True)
    restored = restarted.get(job["job_id"], workspace_id="ws1")
    assert restored is not None
    assert restored["status"] == "completed"

    get_event_store().ingest(
        {"id": "e1", "type": "t", "source": "abbis", "product": "abbis", "workspace_id": "ws1"}
    )
    get_event_store().ingest(
        {"id": "e2", "type": "t", "source": "abbis", "product": "abbis", "workspace_id": "ws1"}
    )
    token, _ = get_token_service().mint(
        product="abbis",
        workspace_id="ws1",
        actor_id="u",
        grants=grants_for_product("abbis"),
        purpose="t",
    )
    stream = client.get(
        "/v1/products/abbis/events/stream",
        headers=_auth(token),
        params={"cursor": 0},
    )
    assert stream.status_code == 200
    body = stream.json()
    assert len(body["events"]) >= 2
    cursor = body["cursor"]
    again = client.get(
        "/v1/products/abbis/events/stream",
        headers=_auth(token),
        params={"cursor": cursor},
    )
    assert again.json()["events"] == []


def test_openapi_and_runtime_agree() -> None:
    assert runtime_agrees_with_openapi("carina")["ok"] is True


def test_connector_cannot_request_arbitrary_url() -> None:
    fake = FakeProductConnector()
    with pytest.raises(ConnectorDenied):
        fake.assert_allowed("GET", "/admin/x")
    with pytest.raises(ConnectorDenied):
        assert_safe_url("http://169.254.169.254/latest/meta-data/")


def test_token_replay_wrong_audience_revoked() -> None:
    tokens = get_token_service()
    once, claims = tokens.mint(
        product="carina",
        workspace_id="ws",
        actor_id="u",
        grants={"*"},
        purpose="once",
    )
    tokens.parse(once, consume_once=True)
    with pytest.raises(ValueError, match="replay"):
        tokens.parse(once, consume_once=True)

    bad, _ = tokens.mint(
        product="carina",
        workspace_id="ws",
        actor_id="u",
        grants={"*"},
        purpose="t",
        audience="other",
    )
    with pytest.raises(ValueError, match="wrong_audience"):
        tokens.parse(bad)

    good, gclaims = tokens.mint(
        product="carina",
        workspace_id="ws",
        actor_id="u",
        grants={"*"},
        purpose="t",
    )
    tokens.revoke(gclaims.jti)
    with pytest.raises(ValueError):
        tokens.parse(good)


@pytest.mark.asyncio
async def test_connector_idempotent_action_no_duplicate() -> None:
    fake = FakeProductConnector(product_key="abbis")
    a = await fake.action("fixture_action", {"message": "x"}, idempotency_key="k1")
    b = await fake.action("fixture_action", {"message": "x"}, idempotency_key="k1")
    assert a["ok"] is True
    assert b.get("idempotent_replay") is True
    assert len(fake.actions) == 1


def test_upgrade_and_rollback_restores_lkg() -> None:
    provision_product("petraclus", activate=True, version="1.0.0")
    upgrade_product("petraclus", version="1.1.0")
    assert get_product_pack_registry().require("petraclus").version == "1.1.0"
    rolled = rollback_product("petraclus")
    assert rolled["status"] == "rolled_back"
    assert get_product_pack_registry().require("petraclus").version == "1.0.0"


def test_repeated_provision_no_duplicate() -> None:
    first = provision_product("petraclus", activate=True, version="1.0.0")
    second = provision_product("petraclus", activate=True, version="1.0.0")
    assert first["status"] == "provisioned"
    assert second.get("duplicate") is True or second["status"] == "already_provisioned"
    plan = plan_provision("petraclus")
    assert plan["idempotent"] is True


def test_kill_switch_preserves_investigation_state() -> None:
    get_job_store().create(
        product="clinicom",
        workspace_id="ws1",
        node_key="pack.ping",
        input_payload={},
    )
    get_event_store().ingest(
        {"id": "keep-1", "type": "t", "source": "clinicom", "product": "clinicom"}
    )
    out = disable_product("clinicom")
    assert out["status"] == "disabled"
    assert out["jobs_preserved"] >= 1
    assert out["events_preserved"] >= 1
    assert get_product_pack_registry().require("clinicom").enabled is False


def test_cross_product_memory_and_metrics(client: TestClient) -> None:
    mem = get_memory_store()
    mem.put(product="abbis", workspace_id="ws1", key="secret", value={"n": 1}, durable=True)
    assert mem.get(product="clinicom", workspace_id="ws1", key="secret") is None

    health = client.get("/v1/products/abbis/health")
    assert health.status_code == 200
    metrics = client.get("/v1/products/abbis/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["product"] == "abbis"


def test_foundation_conformance_ready() -> None:
    report = run_foundation_conformance()
    assert report["ready"] is True
    assert report["signature"]
    assert "must_failures" in report
    assert report["must_failures"] == []


def test_malicious_pack_cannot_escape_grants() -> None:
    registry = get_product_pack_registry()
    with pytest.raises(PackValidationError):
        registry.install(build_fixture_pack("petraclus", corrupt=True))
